"""
Enhanced Multi-Step YAML Configuration Parser
This module provides a multi-step YAML parsing process with:
1. Global include expansion
2. Symbol/keyword resolution database
3. Format validation and checking
4. Final resolved configuration generation
"""

import sys
import os
import threading
import yaml
import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from pathlib import Path
import copy
from collections import ChainMap
from datetime import datetime
from enum import Enum


#include the fileinfo from file_handler
from .file_handler import FileInfo



class ParseStage(Enum):
    """Enumeration of parsing stages"""
    INITIAL = "initial"
    GLOBAL_INCLUDES = "global_includes"
    SYMBOL_RESOLUTION = "symbol_resolution"
    _GLOBAL_SYMBOLS = "global_symbols"
    _ENV_SYMBOLS = "env_Symbols"
    VALIDATION = "validation"
    FINAL_RESOLUTION = "final_resolution"
    SEARCH_HISTORY = "search_history"

class ValidationSeverity(Enum):
    """Validation message severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationResult:
    """Result of validation process"""
    def __init__(self):
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.info: list[dict[str, Any]] = []
    
    def add_message(self, severity: ValidationSeverity, message: str, 
                   location: str = "", suggestion: str = ""):
        """Add a validation message"""
        msg = {
            "message": message,
            "location": location,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
        if severity == ValidationSeverity.ERROR:
            self.errors.append(msg)
        elif severity == ValidationSeverity.WARNING:
            self.warnings.append(msg)
        else:
            self.info.append(msg)
    
    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return len(self.errors) > 0
    
    def save_validation_result(self, dir_path : Union[str, Path], filedb : dict[str, Any]) -> None:
        """
        Save the validation result to a YAML file in the given directory.
        The filename will be validation_result_{md5hash}.yml, where the hash is computed
        from the validation result keys and values for uniqueness.
        """
        dir_path = Path(dir_path)
        if not dir_path.exists:
            raise RuntimeError("Failed to stored YML symbol db file")

        # Prepare a stable string representation for hashing
        # Collect all messages for hashing, sort for deterministic order
        hash_input = repr(sorted((v ) for severity_list in [*self.errors, *self.warnings, *self.info] for k,v in severity_list.items() if k == "message") ).encode("utf-8")
        
        md5_hash = hashlib.md5(hash_input).hexdigest()[:8] # take only first 8 hash

        filename = f"validation_result_{md5_hash}.yml"
        file_path = dir_path / filename

        # Dump the validation result to the YML file
        validation_data = {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(validation_data, f, default_flow_style=False, allow_unicode=True)
        # save the result in DB
        filedb[ParseStage.VALIDATION] =  FileInfo(file_path)

        
    def print_summary(self) -> str:
        """Get a comprehensive  validation summary"""
        summary = f"Validation Summary:\n"
        # add errors if any 
        if self.errors:
            summary += f"  Errors ({len(self.errors)}):\n"
            for error in self.errors:
                summary += f"    - {error['message']} at {error['location']}\n"
        
        # add warning if any 
        if self.warnings:
            summary += f"  Warnings ({len(self.warnings)}):\n"
            for warning in self.warnings:
                summary += f"    - {warning['message']} at {warning['location']}\n"
        
        # add info if any 
        if self.info:
            summary += f"  Info ({len(self.info)}):\n"
            for info in self.info:
                summary += f"    - {info['message']} at {info['location']}\n"
        return summary


class SymbolDatabase:
    """Database for resolving symbols and expressions"""
    
    def __init__(self):
        self.global_symbols: dict[str, Any] = {}
        self.environment_vars: dict[str, str] = {}
        self.computed_symbols: dict[str, Any] = {}
        self.symbol_dependencies: dict[str, set[str]] = {}
    
    def add_global_symbol(self, key: str, value: Any, section_name: str = ""):
        """Add a global symbol to the
            key is the symbol name and value 
            is the symbol value in database"""
        self.global_symbols[key] = {
            'value': value,
            'section': section_name,
            'type': type(value).__name__
        }
    
    def add_environment_var(self, key: str, value: str, section_name : str = ""):
        """Add environment variable (var started with $ENV{VAR_NAME} )
            env variable are decode and then 
            put in the symbol db """
        self.environment_vars[key] = {
            'value': value,
            'section' : section_name,
            'type' : type(value).__name__
        }
    
    def resolve_symbol(self, symbol: str) -> Optional[Any]:
        """Resolve a symbol from the database"""
        # Check global symbols first
        if symbol in self.global_symbols:
            return self.global_symbols[symbol]['value']
        
        # Check environment variables
        if symbol in self.environment_vars:
            return self.environment_vars[symbol]['value']
        
        # Check computed symbols
        if symbol in self.computed_symbols:
            return self.computed_symbols[symbol]
        
        return None
    
    def get_unresolved_symbols(self, text: str) -> List[str]:
        """Find unresolved symbols in text"""
        pattern = r'\$\{([^}:]+)(?::([^}]+))?\}'
        unresolved = []
        
        for match in re.finditer(pattern, text):
            symbol = match.group(1)
            if self.resolve_symbol(symbol) is None:
                unresolved.append(symbol)
        
        return unresolved
    
    def save_symbol_db_files(self, dir_path : Union[str, Path], files_db : dict[str, Any] ) -> None :
        """
        Save the global symbol database to a YAML file in the given directory.
        The filename will be global_symbols_{md5hash}.yml, where the hash is computed
        from the sorted global_symbols keys and values for uniqueness.
        """
        dir_path = Path(dir_path)
        if not dir_path.exists:
            raise RuntimeError("Failed to stored YML symbol db file")

        # Prepare a stable string representation for hashing
        # Sort keys for deterministic hash
        items = sorted((k, v['value']) for k, v in self.global_symbols.items())
        hash_input = repr(items).encode("utf-8")
        md5_hash = hashlib.md5(hash_input).hexdigest()[:8] # take only first 8 hash

        filename = f"global_symbols_{md5_hash}.yml"
        file_path = dir_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.global_symbols, f, default_flow_style=False, allow_unicode=True)

        files_db[ParseStage.SYMBOL_RESOLUTION] = {} # create a new instance of dict to store filedb
        files_db[ParseStage.SYMBOL_RESOLUTION][ParseStage._GLOBAL_SYMBOLS] =  FileInfo(file_path)

        # =================== do the same thing for the ENV variables ========================================
        # Prepare a stable string representation for hashing
        # Sort keys for deterministic hash
        items = sorted((k, v['value']) for k, v in self.environment_vars.items())
        hash_input = repr(items).encode("utf-8")
        md5_hash = hashlib.md5(hash_input).hexdigest()[:8] # take only first 8 hash

        filename = f"env_symbols_{md5_hash}.yml"
        file_path = dir_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.environment_vars, f, default_flow_style=False, allow_unicode=True)

        files_db[ParseStage.SYMBOL_RESOLUTION][ParseStage._ENV_SYMBOLS] =  FileInfo(file_path)
        


# ============================================================================================================
# ----------------------------  EnhancedYAMLParser module for parsing the YML files --------------------------
# ----------------------------   and expand them corerctly  --------------------------------------------------
# ============================================================================================================

#MARK:
class EnhancedYAMLParser:
    """Enhanced YAML parser with multi-step processing"""
    
    _instance: Optional['EnhancedYAMLParser'] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, base_config_dir: Optional[str] = None):
        if EnhancedYAMLParser._initialized:
            return
            
        print("[EnhancedYAMLParser] Initializing multi-step YAML parser")
        
        # Initialize paths
        self.base_config_dir = Path(getattr(sys, '_BASE_PATH', os.getcwd()))
        self.app_data_path = Path(getattr(sys, '_APP_DATA_PATH', './app_data'))
        
        # Create parser directory
        self.parser_dir : Path = self.app_data_path / "parser"
        self.parser_dir.mkdir(parents=True, exist_ok=True)
        
        # # Create subdirectories for different stages
        # self.stages_dir = {
        #     ParseStage.GLOBAL_INCLUDES: self.parser_dir / "global_includes",
        #     ParseStage.SYMBOL_RESOLUTION: self.parser_dir / "symbol_resolution", 
        #     ParseStage.VALIDATION: self.parser_dir / "validation",
        #     ParseStage.FINAL_RESOLUTION: self.parser_dir / "final"
        # }
        # -------------- these dir are not reired
        # for stage_dir in self.stages_dir.values():
        #     stage_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.symbol_db = SymbolDatabase()
        self.validation_result = ValidationResult()
        self.processed_files: dict[str, Union[Any, FileInfo]] = {}
        
        # Known global scope keywords for validation
        self.known_global_keywords = {
            'global', 'application', 'environments', 'include',
            'logger', 'version', 'config', 'settings'
        }
        
        # cerates a file in the search history 
        now_time = datetime.now().strftime("%Y-%m-%d||||_%H:%M:%S:%f")
        file_path = self.parser_dir / f"search_history.yml"
        with open(file_path, "w") as f:
            yaml.dump(f"{'=' *50} Search history {now_time} {'='*50} ", f, default_flow_style=False, sort_keys=False)
        # save search history file
        self.processed_files[ParseStage.SEARCH_HISTORY] = FileInfo(file_path)
        
        EnhancedYAMLParser._initialized = True
    
    def parse_config(self, config_path: Union[str, Path]) -> dict[str, Any]:
        """
        Main entry point for multi-step parsing process
        
        Args:
            config_path: Path to the main configuration file
            
        Returns:
            Fully resolved configuration dictionary
        """
        config_path = self._resolve_path(config_path)
        print(f"[EnhancedYAMLParser] Starting multi-step parsing of {config_path.name}")
        
        try:
            # Step 1: Expand global includes
            global_expanded = self._step1_expand_global_includes(config_path)
            
            # Step 2: Build symbol database
            self._step2_build_symbol_database(global_expanded)
            
            # Step 3: Validate and check format
            self._step3_validate_and_check(global_expanded)
            
            # Step 4: Generate final resolved configuration
            final_config = self._step4_final_resolution(global_expanded)
            
            print("=========== Dumping processed File info ==============================")
            # ============= print the processed files info============(recursive function)
            def print_process_files(file_db : dict[str, Union[str, Any]], space : int = 0):    
                # print the processed file info
                for stage, fileinfo in file_db.items():
                    print(f"{" " * space}stage = [{stage.name}]")
                    if isinstance(fileinfo, FileInfo):
                        print(f"{" " * space}     File: {fileinfo._file_name}")
                        print(f"{" " * space}     RelPath: {fileinfo._rel_path}")
                        print(f"{" " * space}     Size: {fileinfo._size} bytes")
                        print(f"{" " * space}     Type: {fileinfo._file_type}")
                        print(f"{" " * space}     Last Modified: {fileinfo._last_modified}")
                    elif isinstance(fileinfo, dict):
                        # as we go in take the credit
                        space +=5
                        print_process_files(fileinfo, space)
                        # as we go out release the credit 
                        space -= 5
                    else:
                        raise RuntimeError(f"[print_process_files]  cant proceed with unknown {type(fileinfo)}")
                # return final_config
        
            #print the processed files     
            print_process_files(self.processed_files)
        
            return final_config
        except Exception as e:
            # print traceback if failed 
            import traceback
            traceback.print_exc()
        return None
    
    # =========================================================================================================
    # -------------------------------- the methods are defined below ------------------------------------------
    # =========================================================================================================
    
    #MARK: 1. Expand includes
    # =================================[step-1] Expand the symbol include files =======================================
    def _step1_expand_global_includes(self, config_path: Path) -> dict[str, Any]:
        """
        Step 1: Expand only global scope includes and create temp file
        """
        print("[Step 1] Expanding global scope includes...")
        
        # Load the main configuration
        main_config = self._load_yaml_file(config_path)
        
        # Process only global-level includes
        expanded_config = self._process_global_includes(main_config)
        
        # Generate temp file name and store the yml file for dumping 
        config_hash = hashlib.md5(str(config_path).encode()).hexdigest()[:8]
        temp_filename = f"global_expanded_{config_hash}.yml"
        temp_path = self.parser_dir / temp_filename
        
        # Save expanded configuration
        with open(temp_path, 'w') as f:
            yaml.dump(expanded_config, f, default_flow_style=False, sort_keys=False)
        
        # save the processed file in DB
        self.processed_files[ParseStage.GLOBAL_INCLUDES] = FileInfo(temp_path)
        return expanded_config
    
    def _process_global_includes(self, config: dict[str, Any]) -> dict[str, Any]:
        """Process only top-level (global) includes"""
        includes_to_process = []
        
        # Only process includes at the root level
        if 'include' in config:
            value = config.pop('include')
            if isinstance(value, list):
                includes_to_process.extend(value)
            elif isinstance(value, str):
                includes_to_process.append(value)
            else: 
                raise ValueError(f" Except only list and string in include {self.__name__}")
        
        # Process each include
        for include_path in includes_to_process:
            include_full_path = self._resolve_path(include_path)
            include_config = self._load_yaml_file(include_full_path)
            
            # Recursively process includes in the included file
            include_config = self._process_global_includes(include_config)
            
            # Merge with main config
            config = self._deep_merge(config, include_config)
        
        return config
    
    #MARK: 2. Build sym db
    # =================== [step-2] Build symbol database =================================
    def _step2_build_symbol_database(self, config: dict[str, Any]):
        """
        Step 2: Build internal database for symbol resolution
        """
        print("[Step 2] Building symbol resolution database...")
        
        #  for the symbol database we are only using the global and application specified sumbol for right now
        
        self._extract_global_symbols(config)
        
        # now save the symbol db to a file 
        self.symbol_db.save_symbol_db_files(self.parser_dir, self.processed_files)
        print(f"[Step 2] Symbol database built: {len(self.symbol_db.global_symbols)} global symbols, "
              f"{len(self.symbol_db.environment_vars)} env vars")
    
    def _extract_global_symbols(self, config_section: dict[str, Any], section_name: Optional[str] = None):
        """
        Extract global and environment variable symbols from a configuration section,
        following the rules:
        - ENV variable defined using $ENV{VAR_NAME} : VAR_VALUE
        - Normal variable defined using $VAR{VAR_NAME} : VAR_VALUE
        - Only allow VAR_NAME in capital letters, else raise error
        - Only allow symbol definitions at the key position
        - VAR_VALUE must not contain other symbol definitions in its value
        """
        env_pattern = r'^\$ENV\{([A-Z_][A-Z0-9_]*)\}$'
        var_pattern = r'^\$VAR\{([A-Z_][A-Z0-9_]*)\}$'
        symbol_pattern = r'^\$\{([A-Z_][A-Z0-9_]*)\}$'

        def is_symbol_key(key: str) -> tuple[str, str] | None:
            """Return ('ENV'|'VAR', VAR_NAME) if key is a symbol definition, else None"""
            if not isinstance(key, str):
                return None
            m_env = re.match(env_pattern, key)
            if m_env:
                return ('ENV', m_env.group(1))
            m_var = re.match(var_pattern, key)
            if m_var:
                return ('VAR', m_var.group(1))
            return None

        def contains_symbol_definition(val: Any) -> bool:
            """Check if value contains a symbol definition pattern (not expansion)"""
            if isinstance(val, str):
                # Only allow expansion, not definition, in value
                # if re.search(env_pattern, val) or re.search(var_pattern, val) or re.search(symbol_pattern, val):
                # allow symbol defination but not at the key part
                if re.search(env_pattern, val) or re.search(var_pattern, val):
                    return True
            elif isinstance(val, dict):
                for k, v in val.items():
                    # recursively search the dic for capturing the symbol defination
                    if contains_symbol_definition(k) or contains_symbol_definition(v):
                        return True
            return False

        def extract(obj: dict[str, Any], section_name: str = ""):
            for key, value in obj.items():
                symbol_info = is_symbol_key(key)
                

                if symbol_info:
                    var_type, var_name = symbol_info
                    # Check VAR_NAME is all uppercase
                    if not var_name.isupper():
                        raise ValueError(f"VAR_NAME '{var_name}' must be in all capital letters at {section_name}")
                    # Value must not contain symbol definitions
                    if contains_symbol_definition(value):
                        raise ValueError(f"Symbol value for {key} at {section_name} must not contain other symbol definitions")
                    # Add to symbol db
                    if var_type == 'ENV':
                        self.symbol_db.add_environment_var(var_name, value, section_name)
                    elif var_type == 'VAR':
                        self.symbol_db.add_global_symbol(var_name, value, section_name)
                else:
                    # Only allow symbol definitions at key position, not elsewhere
                    if isinstance(value, dict):
                        extract(value, f"{section_name}/{key}" if section_name else key)
                    elif isinstance(value, str):
                        # Expansion is allowed in value, but not definition
                        if contains_symbol_definition(value):
                            raise ValueError(f"Symbol definition not allowed in value at {section_name}")
                    # else: ignore non-dict, non-str

        extract(config_section, section_name)


    #MARK: 3. validation & check
    # ======================[step-3] validation and check ===================================================
    def _step3_validate_and_check(self, config: dict[str, Any]):
        """
        Step 3: Format validation and checking
        """
        print("[Step 3] Running validation and format checking...")
        
        # Check for includes in non-global scopes
        self._validate_include_placement(config)
        
        # Check for unresolved expressions
        self._validate_unresolved_expressions(config)
        
        # Validate known global scope keywords
        self._validate_global_scope_keywords(config)
        
        # Check for circular dependencies
        self._validate_circular_dependencies(config)
        
        # Save validation report
        self.validation_result.save_validation_result( self.parser_dir,self.processed_files)
        
        print(f"[Step 3] ",self.validation_result.print_summary())
    
       
    def _validate_include_placement(self, config: dict[str, Any], path: str = ""):
        """Check for includes in non-global scopes"""
        include_keys = ['include', 'includes']
        
        def check_includes(obj: Any, current_path: str):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{current_path}.{key}" if current_path else key
                    
                    if key in include_keys and current_path != "":
                        self.validation_result.add_message(
                            ValidationSeverity.ERROR,
                            f"Include found in non-global scope",
                            new_path,
                            "Move include to global scope or use inheritance"
                        )
                    
                    check_includes(value, new_path)
        
        check_includes(config, path)
    
    def _validate_unresolved_expressions(self, config: dict[str, Any], path: str = ""):
        """Check for unresolved expressions"""
        def check_expressions(obj: Any, current_path: str):
            if isinstance(obj, str):
                unresolved = self.symbol_db.get_unresolved_symbols(obj)
                for symbol in unresolved:
                    self.validation_result.add_message(
                        ValidationSeverity.ERROR,
                        f"Unresolved symbol: ${{{symbol}}}",
                        current_path,
                        f"Define '{symbol}' in global scope or environment"
                    )
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{current_path}.{key}" if current_path else key
                    check_expressions(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{current_path}[{i}]"
                    check_expressions(item, new_path)
        
        check_expressions(config, path)
    
    def _validate_global_scope_keywords(self, config: dict[str, Any]):
        """Validate known global scope keywords"""
        for key in config.keys():
            if key not in self.known_global_keywords:
                self.validation_result.add_message(
                    ValidationSeverity.INFO,
                    f"Unknown global keyword: '{key}'",
                    key,
                    f"Consider if '{key}' should be in known_global_keywords"
                )
    
    def _validate_circular_dependencies(self, config: dict[str, Any]):
        """Check for circular dependencies in symbol resolution"""
        # This is a simplified check - could be enhanced for more complex scenarios
        pass

    
    #MARK: 4. final resolun.
    # ==============================[step-4] final resolution of the symbols ======================================================
    # ---------------------------------------------------------------------------------------------------------------------
    def _step4_final_resolution(self, resolved_config: dict[str, Any]) -> dict[str, Any]:
        """
        Step 4: Create final resolved configuration
        """
        print("[Step 4] Generating final resolved configuration...")
        
        # Substitute all symbols and expressions
        resolved_config = self._substitute_all_symbols(resolved_config)
        
        # Save final resolved configuration
        final_path = self.parser_dir / "resolved_config.yml"
        with open(final_path, 'w') as f:
            yaml.dump(resolved_config, f, default_flow_style=False, sort_keys=False)
        self.processed_files[ParseStage.FINAL_RESOLUTION]  = FileInfo(final_path)
        
        return resolved_config
    


    def _substitute_all_symbols(self, config: dict[str, Any]) -> Any:
        """
        Substitute all symbols and expressions in the configuration.
        Only expand symbols in the value position, not in keys.
        Environment variables take priority over global symbols.
        """
        if isinstance(config, dict):
            # Only expand in value position, not in keys
            return {key: self._substitute_all_symbols(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._substitute_all_symbols(item) for item in config]
        elif isinstance(config, str):
            return self._resolve_string_expressions(config)
        else:
            return config

    def _resolve_string_expressions(self, text: str) -> str:
        """
        Resolve expressions in a string.
        Environment variables take priority over global symbols.
        Only expand symbols that exist in env or global.
        """
        pattern = r'\$\{([^}:]+)(?::([^}]+))?\}'

        def replacer(match):
            symbol = match.group(1)
            default_value = match.group(2)

            # Check environment vars first, then global
            env_val = self.symbol_db.environment_vars.get(symbol)
            if env_val is not None and 'value' in env_val:
                return str(env_val['value'])
            global_val = self.symbol_db.global_symbols.get(symbol)
            if global_val is not None and 'value' in global_val:
                return str(global_val['value'])
            if default_value is not None:
                return default_value
            # If not found, leave as is
            return match.group(0)

        return re.sub(pattern, replacer, text)
    
    
    #MARK: Util meths
    # =============================================== rest util function for loading the YML files and resolving the path ======================
    # Utility methods from original parser
    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load a YAML file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Failed to load YAML file {file_path}: {e}")
    
    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve a path relative to the base directory """
        path = Path(path)
        
        if path.is_absolute():
            return path
        
        # First try extending the path wrt base_config_dir
        base_config_path = self.base_config_dir / path
        if base_config_path.exists():
            return base_config_path.resolve()
        else:
            # Search recursively in BASE_PATH
            for root, dirs, files in os.walk(self.base_config_dir):
                for file in files:
                    if file == path.name:
                        found_path = Path(root) / file
                        return found_path.resolve()
            
            # Fallback to base_config_dir even if file doesn't exist
            return base_config_path.resolve()
    
    # def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    #     """Deep merge two dictionaries"""
    #     result = copy.deepcopy(base)
        
    #     for key, value in override.items():
    #         if key in result and isinstance(result[key], dict) and isinstance(value, dict):
    #             result[key] = self._deep_merge(result[key], value)
    #         else:
    #             result[key] = copy.deepcopy(value)
        
    #     return result
    
    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries, but for each key, if the value is a string in override,
        it takes precedence and is placed first in the result. For dict values, merge recursively.
        The order of keys in the result will be: all string-valued keys from override (in order),
        then the rest (dicts and others).
        """
        result = {}

        # First, collect all string-valued keys from override
        for key, value in override.items():
            if isinstance(value, str):
                result[key] = value

        # Now, merge the rest (dicts and other types)
        all_keys = set(base.keys()) | set(override.keys())
        for key in all_keys:
            if key in result:
                continue  # already handled string-valued override
            base_val = base.get(key)
            override_val = override.get(key)
            if isinstance(base_val, dict) and isinstance(override_val, dict):
                result[key] = self._deep_merge(base_val, override_val)
            elif key in override:
                result[key] = copy.deepcopy(override_val)
            elif key in base:
                result[key] = copy.deepcopy(base_val)
        return result
    
    def get_validation_report(self) -> ValidationResult:
        """Get the validation report"""
        return self.validation_result
    
    def get_symbol_database(self) -> SymbolDatabase:
        """Get the symbol database"""
        return self.symbol_db

    def save_search_history(self, srch_history : Any) -> None:
        """
        Get the file from the search history and append information to it,
        prefixing each entry with a timestamp.
        """
        # Find the search history file from processed_files
        fileinfo = self.processed_files[ParseStage.SEARCH_HISTORY]
      
        # Prepare the entry with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "data": srch_history
        }
        # Append to the YAML file
        with open(fileinfo._file_path, "a") as f:
            yaml.dump([entry], f, default_flow_style=False, sort_keys=False)


# ============================================================================================================
# ----------------------------  Parser Class for handling the serach matrix operation  -----------------------
# ============================================================================================================
#MARK:
class Parser:
    _instance : Optional['Parser']= None
    _yml_file_parser : Optional[EnhancedYAMLParser]= None
    _lock = threading.Lock()
    # this is the generated YML config that we care about 
    _yml_generated_config :Optional[dict[str, Any]]= None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
        if cls._yml_file_parser is None:
            cls._yml_file_parser = EnhancedYAMLParser()
        return cls._instance
    
    def __init__(self):
        """ initing the singleton instance of the parser 
        """
        # make sure not to called again 
        if Parser._initialized :
            return
        print("[Parser] Initing module")
        self._parser = Parser._yml_file_parser
        
        # parse the YAML file and configure database according to it 
        Parser._yml_generated_config =  self.configure_from_yaml()
        # at this point if YML config is generated properly then we are good to go otherwise 
        # Enhanced YAML parser only give the error and return the result
        
        print(self.search_config_keys('logger.hci_cmd.handlers.file'))
        print(self.search_config_keys('logger.hci_cmd.handlers'))
        sys.exit(0)
        
        # module inited properly
        Parser._initialized = True

    def configure_from_yaml(self, config_path: Optional[Union[str, Path]] = None):
        """
        Configure global settings from YAML file and apply environment variables
        
        Args:
            config_path: Path to the YAML configuration file
        """
        # Load the configuration from YAML file
        if config_path is None:
            config_path = getattr(sys, "_APP_CONFIG_PATH", None)
        config = self._parser.parse_config(config_path)
        
        # Apply environment variables from the configuration
        # self._apply_environment_variables(config)
        
        return config
    
    def _apply_environment_variables(self, config: dict[str, Any]):
        """
        Apply environment variables found in the configuration
        
        Args:
            config: Configuration dictionary
        """
        if not isinstance(config, dict):
            return
            
        for key, value in config.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                self._apply_environment_variables(value)
            elif isinstance(value, str):
                # Check if the string contains environment variable references
                if '${' in value and '}' in value:
                    # Extract environment variable name and set it
                    print(f"Processing environment variable: {value}")
                    env_var_name = self._extract_env_var_name(value)
                    if env_var_name:
                        # Set the environment variable if it's not already set
                        if env_var_name not in os.environ:
                            # Extract default value if present (${VAR:default})
                            default_value = self._extract_default_value(value)
                            os.environ[env_var_name] = default_value or ""
                            print(f"Set environment variable: {env_var_name} = {default_value or ''}")

    # ----------------------------- This method is very useful ---------------------------------------------------------
    def search_config_keys(self, keyword: str):
        """
        Search for items in the _yml_generated_config using provided keywords.
        Uses regex to find similar keys. Prints search history and results.
        Raises ValueError if no results are found.
        
        Args:
            *keywords: Variable number of string keywords to search for.
        
        Returns:
            Dict of matched keys and their values.
        """
        if not hasattr(self, "_yml_generated_config") or self._yml_generated_config is None:
            raise AttributeError("No _yml_generated_config found in the parser instance.")

        config = self._yml_generated_config
        if not isinstance(config, dict):
            raise ValueError("The _yml_generated_config is not a dictionary.")

        search_history = []
        # result can either be a dic or value
        result = None
        
        # Split the keyword by '.' to create a nested dict structure
        # Example: "logger.default.log_level.file_io.max_size" -> 
        # {'logger': {'default': {'log_level': {'file_io': {'max_size': None}}}}}

        keywords = keyword.split('.')

        while len(keywords) > 0:
            # get the first ele of keyword
            keyword = keywords.pop(0)
            
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            similar_pattern = re.compile(rf".*{re.escape(keyword)}.*", re.IGNORECASE)
            
            # for every key in the config we will set found to false 
            found = False
            # search in the config dictionary
            for key in config.keys():
                # if patterns match the key then again search in that 
                if pattern.fullmatch(key):
                    # if found then we will set found to true
                    found = True
                    # set the result to the value of the key
                    result = config = config[key]
                    search_history.append(
                        f"Exact match for '{keyword}' -> '{key}'"
                    )
                elif similar_pattern.match(key):
                    # if found then we will set found to true
                    found = True
                    # set the result to the value of the key
                    result = config = config[key]
                    search_history.append(
                        f"Similar match for '{keyword}' -> '{key}'"
                    )
                    
            # check if found is still false then we don't found the key
            if not found:
                # if not found then we will add the search history
                search_history.append(
                    f"No match found for '{keyword}'"
                )
                # immediately breaks if not found afterwards 
                result = None
                # immediately breaks if not found afterwards 
                break

        # save the search hostory 
        self._parser.save_search_history(search_history)

        return result

# create a parser global instance and return this only when anyone tries to create new one 
global_parser = Parser()

def global_setting_parser() -> {Parser}:
    global global_parser
    if global_parser is None:
        global_parser = Parser()
    return global_parser




# Test function
def test_enhanced_parser():
    """Test the enhanced YAML parser"""
    parser = EnhancedYAMLParser()
    
    # Test with the provided configuration
    try:
        config = parser.parse_config()
        print("Final configuration loaded successfully!")
        print(f"Configuration keys: {list(config.keys())}")
        
        # Print validation results
        validation = parser.get_validation_report()
        print(f"\n{validation.get_summary()}")
        
        return config
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None

if __name__ == "__main__":
    test_enhanced_parser()