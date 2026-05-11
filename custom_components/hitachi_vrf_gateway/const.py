"""Constants for the Hitachi VRF Gateway integration."""

DOMAIN = "hitachi_vrf_gateway"

# Config entry keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_DEVICES = "devices"
CONF_GATEWAY_NAME = "name"

# Defaults
DEFAULT_NAME = "Hitachi VRF Gateway"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_VERIFY_SSL = False

# API params
API_MOD_AUTH = "0"
API_ACT_LOGIN = "1"
API_MOD_DEVICE = "3"
API_ACT_STATUS = "35"
API_ACT_CONTROL = "33"

# Device field names (match the gateway web form exactly)
FIELD_POWER = "OnOf"
FIELD_MODE = "OpeM"
FIELD_FAN = "FanS"
FIELD_TEMP = "Ts"

# Power values
POWER_ON = "1"
POWER_OFF = "0"

# Mode values
MODE_HEAT = "2"
MODE_FAN = "1"
MODE_DRY = "64"
MODE_COOL = "4"

# Fan speed values
FAN_WEAK = "0"
FAN_STRONG = "1"
FAN_SHARP = "2"
FAN_SUPER = "18"
FAN_AUTO = "32"

# Temperature limits
TEMP_MIN = 17.0
TEMP_MAX = 30.0
TEMP_STEP = 0.5
