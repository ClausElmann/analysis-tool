# TEMP STATE

mode: HARVEST_READY
pipeline: angular_harvest_v2
status: CLEAN

directives:
- (empty)

stop_conditions:
- UNKNOWN → stop
- FAIL spike → stop
