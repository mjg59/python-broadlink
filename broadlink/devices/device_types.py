from dev_a1       import a1
from dev_dooya    import dooya
from dev_mp1      import mp1
from dev_rm       import rm
from dev_s1c      import S1C
from sp2mini2_dev import sp2mini2
from dev_spx      import sp1,sp2
from device       import device

# returns an instance of the devices according to the MAC address
def gendevice(devtype, host, mac):
  if devtype == 0: # SP1
    return sp1(host=host, mac=mac)
  if devtype == 0x2711: # SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2719 or devtype == 0x7919 or devtype == 0x271a or devtype == 0x791a: # Honeywell SP2
    return sp2(host=host, mac=mac)
  if devtype == 0x2720: # SPMini
    return sp2(host=host, mac=mac)
  elif devtype == 0x753e: # SP3
    return sp2(host=host, mac=mac)
  elif devtype == 0x947a or devtype == 0x9479: # SP3S
    return sp2(host=host, mac=mac)
  elif devtype == 0x2728: # SPMini2
    return sp2mini2(host=host, mac=mac)
  elif devtype == 0x2733 or devtype == 0x273e: # OEM branded SPMini
    return sp2(host=host, mac=mac)
  elif devtype >= 0x7530 and devtype <= 0x7918: # OEM branded SPMini2
    return sp2(host=host, mac=mac)
  elif devtype == 0x2736: # SPMiniPlus
    return sp2(host=host, mac=mac)
  elif devtype == 0x2712: # RM2
    return rm(host=host, mac=mac)
  elif devtype == 0x2737: # RM Mini
    return rm(host=host, mac=mac)
  elif devtype == 0x273d: # RM Pro Phicomm
    return rm(host=host, mac=mac)
  elif devtype == 0x2783: # RM2 Home Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x277c: # RM2 Home Plus GDT
    return rm(host=host, mac=mac)
  elif devtype == 0x272a: # RM2 Pro Plus
    return rm(host=host, mac=mac)
  elif devtype == 0x2787: # RM2 Pro Plus2
    return rm(host=host, mac=mac)
  elif devtype == 0x278b: # RM2 Pro Plus BL
    return rm(host=host, mac=mac)
  elif devtype == 0x278f: # RM Mini Shate
    return rm(host=host, mac=mac)
  elif devtype == 0x2714: # A1
    return a1(host=host, mac=mac)
  elif devtype == 0x4EB5 or devtype == 0x4EF7: # MP1: 0x4eb5, honyar oem mp1: 0x4ef7
    return mp1(host=host, mac=mac)
  elif devtype == 0x2722: # S1 (SmartOne Alarm Kit)
    return S1C(host=host, mac=mac)
  elif devtype == 0x4E4D: # Dooya DT360E (DOOYA_CURTAIN_V2)
    return dooya(host=host, mac=mac)
  else:
    return device(host=host, mac=mac)