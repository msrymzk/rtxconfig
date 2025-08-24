import logging
import netmiko

log = logging.getLogger(__name__)

if not getattr(netmiko, "_MY_PATCH_APPLIED", False):
    OriginalClass = netmiko.BaseConnection
    _orig = OriginalClass.read_until_pattern

    def patched(self, *args, **kwargs):
        if kwargs['pattern'] == '>':
            kwargs['pattern'] = '(?:>|#)'
        elif kwargs['pattern'] == '>.*':
            kwargs['pattern'] = '(?:>.*$|#.*$)'
        log.debug(f"patched set_base_prompt start with args: {args}, kwargs: {kwargs}")
        result = _orig(self, *args, **kwargs)
        log.debug(f"patched set_base_prompt finish with result: {result}")
        return result

    OriginalClass.read_until_pattern = patched
    netmiko._MY_PATCH_APPLIED = True
    log.info("Applied monkey patch to ConnectHandler.set_base_prompt")
