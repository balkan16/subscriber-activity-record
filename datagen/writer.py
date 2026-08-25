
def write_file(path, records,spec,source):
    with open(path, 'wb') as f:
        for alternative, record in records:
            f.write(spec.encode(source,(alternative,record)))
            

def read_file(path,spec,source):
    offset = 0
    records = []
    with open(path, 'rb') as f:
        bytes = f.read()
    while offset < len(bytes):
        record, used = spec.decode_with_length(source, bytes[offset:])
        offset += used
        records.append(record)
    return records



if __name__ == "__main__":
    from packing import tbcd, address, bits, SCC, CAMEL
    import asn1tools
    spec = asn1tools.compile_files(['../docs/cdr-format.asn'])
    T0 = bytes.fromhex('2608050914002b0700')   # 09:14:00 +07:00
    T1 = bytes.fromhex('2608050921112b0700')   # 09:21:11
    T2 = bytes.fromhex('2608050928402b0700')   # 09:28:40
    NODE   = 'PGW-JKT-01'
    MSISDN = bytes.fromhex('91261891318471')   # your packed MSISDN
    IMSI   = bytes.fromhex('15900941563728f6') # your packed IMSI
    
    FILE_HEADER = {
    'fileLength':          0,          # filled in once the file is written
    'fileSequenceNumber':  4417,
    'senderNodeId':        NODE,
    'fileOpenTimeStamp':   T0,
    'lastAppendTimeStamp': T2,
    'recordCount':         3,
    'fileClosureReason':   'timeLimit',
    'lostRecordIndicator': False,
}

    DATA_1 = {
    'recordType':                85,
    'p-GWAddress':               address('0a000001'),
    'chargingID':                3355901,
    'servingNodeAddress':        [address('0a000002')],
    'accessPointNameNI':         'internet',
    'recordOpeningTime':         T0,
    'duration':                  431,
    'causeForRecClosing':        22,               # rATChange — more follow
    'recordSequenceNumber':      1,
    'nodeID':                    NODE,
    'localSequenceNumber':       884213,
    'servedMSISDN':              MSISDN,
    'servedIMSI':                IMSI,
    'chargingCharacteristics':   bytes.fromhex('0800'),
    'servingNodePLMNIdentifier': bytes.fromhex('510990'),
    'rATType':                   6,                # 4G for this record
    'servingNodeType':           ['mME'],
    'listOfServiceData': [
        {   # general internet — quota ran out, prompting re-authorisation
            'ratingGroup':            10,
            'serviceConditionChange': bits(['dCCAVolumeExhausted'], SCC, 27),
            'timeOfReport':           T1,
            'timeUsage':              431,
            'datavolumeFBCUplink':    412_118,
            'datavolumeFBCDownlink':  8_903_744,
        },
        {   # video bundle — closed because the record closed
            'ratingGroup':            20,
            'serviceConditionChange': bits(['recordClosure'], SCC, 27),
            'timeOfReport':           T1,
            'timeUsage':              210,
            'datavolumeFBCUplink':    44_300,
            'datavolumeFBCDownlink':  3_120_500,
        },
    ],
}


# Record 2 — same session, after the technology change. Ends normally.
DATA_2 = {
    'recordType':                85,
    'p-GWAddress':               bytes.fromhex('0a000001'),
    'chargingID':                3355901,          # same session
    'servingNodeAddress':        [bytes.fromhex('0a000002')],
    'accessPointNameNI':         'internet',
    'recordOpeningTime':         T1,
    'duration':                  449,
    'causeForRecClosing':        0,                # normalRelease — last one
    'recordSequenceNumber':      2,
    'nodeID':                    NODE,
    'localSequenceNumber':       884597,
    'servedMSISDN':              MSISDN,
    'servedIMSI':                IMSI,
    'chargingCharacteristics':   bytes.fromhex('0800'),
    'servingNodePLMNIdentifier': bytes.fromhex('510990'),
    'rATType':                   2,                # 3G now
    'servingNodeType':           ['mME'],
    'listOfServiceData': [
        {
            'ratingGroup':            10,
            'serviceConditionChange': bits(['pDPContextRelease'], SCC, 27),
            'timeOfReport':           T2,
            'timeUsage':              449,
            'datavolumeFBCUplink':    198_400,
            'datavolumeFBCDownlink':  2_441_100,
        },
    ],
}


# Record 3 — an outgoing call by the same subscriber.
CALL = {
    'recordType':          0,
    'servedIMSI':          IMSI,
    'servedMSISDN':        MSISDN,
    'callingNumber':       MSISDN,
    'calledNumber':        bytes.fromhex('91857718892720'),
    'recordingEntity':     bytes.fromhex('91857710000010'),
    'location':            {'locationAreaCode': bytes.fromhex('0001'),
                            'cellId':           bytes.fromhex('00a8')},
    'callDuration':        183,
    'causeForTerm':        0,
    'callReference':       bytes.fromhex('000d671f'),
    'sequenceNumber':      1,
    'serviceKey':          2,
    'levelOfCAMELService': bits(['callDurSupervision'], CAMEL, 3),
}


# The file, in order. Each element is a choice: alternative name, then the dict.
USAGE_FILE = [
    ('fileHeader', FILE_HEADER),
    ('data',       DATA_1),
    ('data',       DATA_2),
    ('moCall',     CALL),
]

records = [
        ('data',   DATA_1),
        ('data',   DATA_2),
        ('moCall', CALL),
    ]
records = [('data', DATA_1), ('data', DATA_2), ('moCall', CALL)]
write_file("usage.cdr", USAGE_FILE, spec, "UsageRecord")

back = read_file("usage.cdr", spec, "UsageRecord")
print(back)