"""
YAML Configuration Parser with Inheritance Support
This module provides functionality for parsing YAML configuration files
with support for inheritance, includes, and environment variable substitution.
"""

import os
import yaml
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import copy
from collections import ChainMap


class YAMLConfigParser:
    """
    Enhanced YAML configuration parser with inheritance and include support
    """
    
    def __init__(self, base_config_dir: Optional[str] = None):
        """
        Initialize the YAML parser
        
        Args:
            base_config_dir: Base directory for resolving relative paths
        """
        self.base_config_dir = Path(base_config_dir) if base_config_dir else Path.cwd()
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        
    def load_config(self, config_path: Union[str, Path], 
                   use_cache: bool = True) -> Dict[str, Any]:
        """
        Load a YAML configuration file with inheritance support
        
        Args:
            config_path: Path to the YAML configuration file
            use_cache: Whether to use cached configurations
            
        Returns:
            Parsed configuration dictionary
        """
        config_path = self._resolve_path(config_path)
        
        # Check cache
        if use_cache and str(config_path) in self._config_cache:
            return copy.deepcopy(self._config_cache[str(config_path)])
        
        # Load the raw config
        raw_config = self._load_yaml_file(config_path)
        
        # Process inheritance
        processed_config = self._process_inheritance(raw_config, config_path.parent)
        
        # Process includes
        processed_config = self._process_includes(processed_config, config_path.parent)
        
        # Substitute environment variables
        processed_config = self._substitute_env_vars(processed_config)
        
        # Cache the result
        self._config_cache[str(config_path)] = processed_config
        
        return copy.deepcopy(processed_config)
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a YAML file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Failed to load YAML file {file_path}: {e}")
    
    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve a path relative to the base directory"""
        path = Path(path)
        if not path.is_absolute():
            path = self.base_config_dir / path
        return path.resolve()
    
    def _process_inheritance(self, config: Dict[str, Any], 
                           current_dir: Path) -> Dict[str, Any]:
        """
        Process configuration inheritance
        
        Supports multiple inheritance patterns:
        - inherits: parent_config.yml
        - extends: [config1.yml, config2.yml]
        - base: parent_config.yml
        """
        inheritance_keys = ['inherits', 'extends', 'base', 'inherits_from']
        
        # Find inheritance directive
        parent_configs = []
        for key in inheritance_keys:
            if key in config:
                parent_value = config.pop(key)
                if isinstance(parent_value, str):
                    parent_configs.append(parent_value)
                elif isinstance(parent_value, list):
                    parent_configs.extend(parent_value)
        
        if not parent_configs:
            return config
        
        # Load parent configurations
        parent_dicts = []
        for parent_path in parent_configs:
            parent_full_path = current_dir / parent_path
            parent_dict = self.load_config(parent_full_path)
            parent_dicts.append(parent_dict)
        
        # Merge configurations (parents first, then current)
        # Using ChainMap for efficient merging
        if parent_dicts:
            # Deep merge all parent configs and current config
            merged = {}
            for parent in parent_dicts:
                merged = self._deep_merge(merged, parent)
            merged = self._deep_merge(merged, config)
            return merged
        
        return config
    
    def _process_includes(self, config: Dict[str, Any], 
                         current_dir: Path) -> Dict[str, Any]:
        """
        Process configuration includes
        
        Supports:
        - include: file.yml
        - includes: [file1.yml, file2.yml]
        """
        include_keys = ['include', 'includes']
        
        for key in include_keys:
            if key in config:
                include_value = config.pop(key)
                includes = [include_value] if isinstance(include_value, str) else include_value
                
                for include_path in includes:
                    include_full_path = current_dir / include_path
                    include_config = self.load_config(include_full_path)
                    config = self._deep_merge(config, include_config)
        
        return config
    
    def _deep_merge(self, base: Dict[str, Any], 
                    override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries
        
        Args:
            base: Base dictionary
            override: Dictionary to merge into base
            
        Returns:
            Merged dictionary
        """
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in configuration
        
        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax
        """
        if isinstance(config, str):
            # Pattern for ${VAR} or ${VAR:default}
            pattern = r'\$\{([^}:]+)(?::([^}]+))?\}'
            
            def replacer(match):
                var_name = match.group(1)
                default_value = match.group(2)
                return os.environ.get(var_name, default_value or match.group(0))
            
            return re.sub(pattern, replacer, config)
        
        elif isinstance(config, dict):
            return {key: self._substitute_env_vars(value) 
                   for key, value in config.items()}
        
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        
        return config
    
    def get_logger_config(self, logger_name: str, 
                         config_file: Union[str, Path]) -> Dict[str, Any]:
        """
        Get configuration for a specific logger
        
        Args:
            logger_name: Name of the logger
            config_file: Path to the configuration file
            
        Returns:
            Logger-specific configuration
        """
        full_config = self.load_config(config_file)
        
        # Look for logger-specific configuration
        loggers_config = full_config.get('loggers', {})
        
        # Check direct logger name
        if logger_name in loggers_config:
            logger_config = loggers_config[logger_name]
        else:
            # Check patterns (e.g., "A2DP_*" matches "A2DP_logger")
            logger_config = {}
            for pattern, config in loggers_config.items():
                if self._matches_pattern(logger_name, pattern):
                    logger_config = self._deep_merge(logger_config, config)
        
        # Merge with defaults
        default_config = full_config.get('default_logger', {})
        final_config = self._deep_merge(default_config, logger_config)
        
        # Add global settings
        if 'global' in full_config:
            final_config['global'] = full_config['global']
        
        return final_config
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a logger name matches a pattern"""
        # Convert simple wildcards to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{regex_pattern}$', name))
    
    def reload_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Reload a configuration file, clearing cache
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Reloaded configuration
        """
        config_path = self._resolve_path(config_path)
        
        # Clear cache for this file
        cache_key = str(config_path)
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
        
        return self.load_config(config_path, use_cache=False)


# Example YAML configuration structure:
# EXAMPLE_YAML_CONFIG = """
# # logger.yml - Main logger configuration
# global:
#   log_dir: ${LOG_DIR:/var/log/app}
#   max_file_size: 10485760  # 10 MB
#   max_files: 5
#   date_format: "%Y-%m-%d %H:%M:%S"
  
# default_logger:
#   level: INFO
#   handlers:
#     console:
#       enabled: true
#       level: INFO
#     file:
#       enabled: true
#       level: DEBUG
#       filename: ${LOG_DIR}/app.log
#     log_window:
#       enabled: false
#       level: DEBUG
#   format: "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
#   propagate: false

# loggers:
#   # Base ACL logger configuration
#   ACL_logger:
#     level: DEBUG
#     handlers:
#       file:
#         filename: ${LOG_DIR}/acl.log
#         max_size: 5242880  # 5 MB
#       console:
#         enabled: false
#     format: "[%(asctime)s] [ACL] [%(levelname)s] %(message)s"
  
#   # A2DP logger inherits from ACL
#   A2DP_logger:
#     inherits: acl_logger_config.yml  # External inheritance
#     level: INFO  # Override parent level
#     handlers:
#       file:
#         filename: ${LOG_DIR}/a2dp.log
#       log_window:
#         enabled: true
#     additional_fields:
#       module: "A2DP"
#       version: "1.0"
  
#   # Pattern-based configuration
#   "Test_*":
#     level: DEBUG
#     handlers:
#       console:
#         enabled: true
# """

# # Example child configuration file (acl_logger_config.yml):
# ACL_LOGGER_CONFIG_EXAMPLE = """
# # acl_logger_config.yml
# level: DEBUG
# handlers:
#   file:
#     enabled: true
#     filename: ${LOG_DIR}/acl_base.log
#     mode: "a"
#     encoding: "utf-8"
#     max_size: 10485760
#     backup_count: 3
#   console:
#     enabled: false
#   syslog:
#     enabled: true
#     address: "/dev/log"
#     facility: "local0"
# format: "[%(asctime)s] [%(threadName)s] [ACL:%(name)s] [%(levelname)s] %(message)s"
# filters:
#   - type: "module"
#     name: "bluetooth.acl"
#     enabled: true
# """