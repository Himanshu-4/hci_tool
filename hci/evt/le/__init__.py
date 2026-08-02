"""
LE (Low Energy) events package

This package provides implementations for BLE HCI events.
"""

from .le_events import (
    # Event classes
    LeConnectionCompleteEvent,
    LeAdvertisingReportEvent,
    LeConnectionUpdateCompleteEvent,
    LeReadRemoteFeaturesCompleteEvent,
    
    # Helper functions
    le_connection_complete,
    le_advertising_report,
    le_connection_update_complete,
    le_read_remote_features_complete,
)

from .poc_le_events import (
    LeDataLengthChangeEvent,
    LeEnhancedConnectionCompleteEvent,
    LePhyUpdateCompleteEvent,
)

from .ext_events import (
    LeExtendedAdvertisingReportEvent,
    LePeriodicAdvertisingSyncEstablishedEvent,
    LePeriodicAdvertisingReportEvent,
    LePeriodicAdvertisingSyncLostEvent,
    LeScanTimeoutEvent,
    LeAdvertisingSetTerminatedEvent,
    LeScanRequestReceivedEvent,
    LeChannelSelectionAlgorithmEvent,
    ext_event_type_str,
    phy_name,
)

from .cs_events import (
    LeCsReadRemoteSupportedCapabilitiesCompleteEvent,
    LeCsReadRemoteFaeTableCompleteEvent,
    LeCsSecurityEnableCompleteEvent,
    LeCsConfigCompleteEvent,
    LeCsProcedureEnableCompleteEvent,
    LeCsSubeventResultEvent,
    LeCsSubeventResultContinueEvent,
    LeCsTestEndCompleteEvent,
)

from .adv_data import (
    AdFlags,
    AdType,
    AdvertisingData,
    AdvertisingDataBuilder,
    parse_adv_data,
)

# Re-export everything to make public API cleaner
__all__ = [
    'LeEnhancedConnectionCompleteEvent',
    'LeDataLengthChangeEvent',
    'LePhyUpdateCompleteEvent',
    'AdType',
    'AdFlags',
    'AdvertisingData',
    'AdvertisingDataBuilder',
    'parse_adv_data',
    # Event classes
    'LeConnectionCompleteEvent',
    'LeAdvertisingReportEvent',
    'LeConnectionUpdateCompleteEvent',
    'LeReadRemoteFeaturesCompleteEvent',
    
    # Helper functions
    'le_connection_complete',
    'le_advertising_report',
    'le_connection_update_complete',
    'le_read_remote_features_complete',

    # extended / periodic advertising and scanning
    'LeExtendedAdvertisingReportEvent',
    'LePeriodicAdvertisingSyncEstablishedEvent',
    'LePeriodicAdvertisingReportEvent',
    'LePeriodicAdvertisingSyncLostEvent',
    'LeScanTimeoutEvent',
    'LeAdvertisingSetTerminatedEvent',
    'LeScanRequestReceivedEvent',
    'LeChannelSelectionAlgorithmEvent',
    'ext_event_type_str',
    'phy_name',

    # channel sounding
    'LeCsReadRemoteSupportedCapabilitiesCompleteEvent',
    'LeCsReadRemoteFaeTableCompleteEvent',
    'LeCsSecurityEnableCompleteEvent',
    'LeCsConfigCompleteEvent',
    'LeCsProcedureEnableCompleteEvent',
    'LeCsSubeventResultEvent',
    'LeCsSubeventResultContinueEvent',
    'LeCsTestEndCompleteEvent',
]