from datetime import datetime, timezone, timedelta
from string import digits
import zoneinfo
from zoneinfo import ZoneInfo
WIB = ZoneInfo('Asia/Jakarta')

FLAGS = {'barred': 0, 
         'suspended': 1, 
         'expired': 2
         }
FLAGS_TOTAL = 3

CAMEL = {'basic': 0, 
         'onlineCharging': 1, 
         'callDurSupervision': 2
         }
CAMEL_TOTAL = 3
SCC   = {'qoSChange': 0, 'sGSNChange' :1, 'sGSNPLMNIDChange' :2, 
         'tariffTimeSwitch' :3,'pDPContextRelease' :4, 'rATChange' :5, 'serviceIdledOut' :6, 
         'configurationChange' :8,'serviceStop' :9, 'dCCATimeThresholdReached' :10, 
         'dCCAVolumeThresholdReached' :11,'dCCATimeExhausted' :13, 'dCCAVolumeExhausted' :14, 
         'dCCAValidityTimeout' :15,'dCCAReauthorisationRequest' :17, 'dCCAContinueOngoingSession' :18,
         'dCCATerminateOngoingSession' :20, 'cGI-SAIChange' :21, 'rAIChange' :22,
         'recordClosure' :24, 'timeLimit' :25, 'volumeLimit' :26, 
         'envelopeClosure' :28,'eCGIChange' :29, 'tAIChange' :30, 'userLocationChange' :31
         }  
SCC_TOTAL = 27

def bits(names, table, total):
    value = bytearray((total+7) // 8)
    for name in names:
        if name in table:
            value[table[name]//8]|= 0x80 >> (table[name] % 8)

    return bytes(value),total

def unbits(value: (bytes, int), table):
    names = []
    buf,tot = value
    for byte_index, byte in enumerate(buf):
        bit_string=bin(byte)[2:].zfill(8)
        for i in range(8):
            if bit_string[i] == '1':
                glob_position = byte_index * 8 + i
                for name, position in table.items():
                    if glob_position == position:
                        names.append(name)
    return names


    

def tbcd(digits: str) -> bytes:
    if not digits.isdigit():
        raise ValueError("Input must be a string of digits.")
    if len(digits) % 2 != 0:
        digits += 'F'

    return bytes(int(digits[i+1] + digits[i], 16) for i in range(0, len(digits), 2))

def untbcd(byte_s: bytes) -> str:
    if byte_s.hex().upper()[-2] == 'F':
        return (''.join(byte_s.hex()[i:i+2][::-1] for i in range(0, len(byte_s.hex()), 2)))[:-1]
    else:
        return (''.join(byte_s.hex()[i:i+2][::-1] for i in range(0, len(byte_s.hex()), 2)))


def address(digits):
    if len(digits) % 2 == 0:
        return bytes.fromhex('91'+''.join([digits[i:i+2][::-1] for i in range(0, len(digits), 2)]))
    else:
        digits += 'F'
        return bytes.fromhex('91'+''.join([digits[i:i+2][::-1] for i in range(0, len(digits), 2)]))

def unaddress(hex_digits):
    if hex_digits.hex().upper()[-2] == 'F':
        return (''.join(hex_digits.hex()[i:i+2][::-1] for i in range(0, len(hex_digits.hex()), 2)))[:-1][2:]
    else:
        return (''.join(hex_digits.hex()[i:i+2][::-1] for i in range(0, len(hex_digits.hex()), 2)))[2:]


def timestamp(dt: datetime):
    ts = dt.strftime('%y%m%d%H%M%S%z')
    return bytes.fromhex(ts[:-5]) + ts[-5].encode() + bytes.fromhex(ts[-4:])

def untimestamp(ts: bytes) -> datetime:
   return datetime.strptime('20'+ts[:6].hex()+ts[6:7].decode()+ts[7:].hex(), '%Y%m%d%H%M%S%z')
    
1

if __name__ == "__main__":
    msisdn = '60123456789'
    hex_msisdn = tbcd(msisdn)
    print(f"MSISDN: {msisdn}")
    print(f"Hex MSISDN: {hex_msisdn}")
    print(f"Unpacked MSISDN: {untbcd(hex_msisdn)}")
    print(f"Address: {address(msisdn)}")
    print(f"Unaddress: {unaddress(address(msisdn))}")
    for n in ["628111631604", "6512345678", "60123456789"]:
        assert unaddress(address(n)) == n

    
    print(f"Timestamp: {timestamp(datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo('Asia/Jakarta')))}")
    print(f"Untimestamp: {untimestamp(timestamp(datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo('Asia/Jakarta'))))}")
    for dt in [
        datetime(2026, 8, 5, 9, 14, 0, tzinfo=WIB),
        datetime(2026, 12, 31, 23, 59, 45, tzinfo=WIB),
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=-5))),
    ]:
        assert untimestamp(timestamp(dt)) == dt, dt
    a = bits(['qoSChange', 'sGSNChange', 'sGSNPLMNIDChange'], SCC, SCC_TOTAL)
    print(a)
    print(unbits(a, SCC))
    assert set(unbits(bits(['rATChange','volumeLimit'], SCC, 27), SCC)) == {'rATChange','volumeLimit'}
