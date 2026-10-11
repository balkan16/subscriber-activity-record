import random
from datetime import timedelta

from datagen.packing import tbcd, address, timestamp, bits, SCC, SCC_TOTAL, CAMEL, CAMEL_TOTAL

EUTRAN = 6
UTRAN = 1
GERAN = 2

CONTINUES = [22, 16, 17]
ENDS = [0, 0, 0, 0, 4]

CONTAINER_REASON = {
    22: ['rATChange'],
    16: ['volumeLimit'],
    17: ['timeLimit'],
    0: ['pDPContextRelease'],
    4: ['pDPContextRelease'],
}

RATING_GROUPS = [10, 20, 30]

CALL_CAUSES = [0, 0, 0, 0, 0, 0, 5, 4]

DESTINATION_PREFIXES = ['62811', '62812', '62813', '62857', '62858', '62877', '62878', '62895', '62896']
FOREIGN_PREFIXES = ['6581', '6591', '60123', '60196']


class SessionGenerator:
    def __init__(self, nodes, msc_nodes, rng=None, omit_rate=0.2, call_interrupt_rate=0.15):
        self.nodes = nodes
        self.msc_nodes = msc_nodes
        self.rng = rng or random.Random()
        self.omit_rate = omit_rate
        self.call_interrupt_rate = call_interrupt_rate
        self.charging_id = 3000000
        self.local_sequence = {node: 0 for node in nodes}
        self.call_reference = 0
        self.message_reference = 0

    def _omit(self):
        return self.rng.random() < self.omit_rate

    def _record_count(self):
        return self.rng.choices([1, 2, 3, 4], weights=[70, 18, 8, 4])[0]

    def _other_party(self):
        if self.rng.random() < 0.05:
            prefix = self.rng.choice(FOREIGN_PREFIXES)
            return prefix + ''.join(str(self.rng.randrange(10)) for _ in range(11 - len(prefix)))
        prefix = self.rng.choice(DESTINATION_PREFIXES)
        return prefix + ''.join(str(self.rng.randrange(10)) for _ in range(12 - len(prefix)))

    def _msc(self):
        index = self.rng.randrange(len(self.msc_nodes))
        return address(f'6281100{index:05d}')

    def _location(self):
        return {
            'locationAreaCode': self.rng.randrange(1, 0x10000).to_bytes(2, 'big'),
            'cellId': self.rng.randrange(1, 0x10000).to_bytes(2, 'big'),
        }

    def data_session(self, msisdn, imsi, start):
        self.charging_id += 1
        node = self.rng.choice(self.nodes)
        count = self._record_count()
        rat = self.rng.choices([EUTRAN, UTRAN, GERAN], weights=[80, 15, 5])[0]
        records = []
        opened = start
        for position in range(1, count + 1):
            last = position == count
            cause = self.rng.choice(ENDS) if last else self.rng.choice(CONTINUES)
            interrupt = not last and self.rng.random() < self.call_interrupt_rate
            if interrupt:
                cause = 22
            duration = self.rng.randrange(30, 1800)
            closed = opened + timedelta(seconds=duration)
            records.append(('data', self._data_record(msisdn, imsi, node, rat, opened, closed, duration,
                                                      cause, position if count > 1 else None)))
            opened = closed
            if interrupt:
                call = self.call(msisdn, imsi, opened, self.rng.choice(['mo', 'mt']))
                records.append(call)
                opened += timedelta(seconds=call[1]['callDuration'])
            elif cause == 22:
                rat = self.rng.choice([r for r in (EUTRAN, UTRAN, GERAN) if r != rat])
        return records

    def _data_record(self, msisdn, imsi, node, rat, opened, closed, duration, cause, sequence):
        self.local_sequence[node] += 1
        record = {
            'recordType': 85,
            'p-GWAddress': bytes([10, 0, 0, 1 + self.nodes.index(node)]),
            'chargingID': self.charging_id,
            'servingNodeAddress': [bytes([10, 1, 0, self.rng.randrange(1, 255)])],
            'recordOpeningTime': timestamp(opened),
            'duration': duration,
            'causeForRecClosing': cause,
            'nodeID': node,
            'localSequenceNumber': self.local_sequence[node],
            'servedMSISDN': address(msisdn),
            'chargingCharacteristics': b'\x08\x00',
            'servingNodeType': ['mME'] if rat == EUTRAN else ['sGSN'],
            'listOfServiceData': self._containers(opened, closed, duration, cause),
        }
        if sequence is not None:
            record['recordSequenceNumber'] = sequence
        if not self._omit():
            record['servedIMSI'] = tbcd(imsi)
        if not self._omit():
            record['accessPointNameNI'] = 'internet'
        if not self._omit():
            record['rATType'] = rat
        if not self._omit():
            record['servingNodePLMNIdentifier'] = b'\x51\x09\x90'
        return record

    def _containers(self, opened, closed, duration, cause):
        groups = self.rng.sample(RATING_GROUPS, self.rng.choice([1, 1, 2, 3]))
        containers = []
        for group in sorted(groups):
            reasons = list(CONTAINER_REASON[cause])
            if self.rng.random() < 0.2:
                reasons.append('dCCAVolumeThresholdReached')
            used = self.rng.randrange(1, duration + 1)
            container = {
                'ratingGroup': group,
                'serviceConditionChange': bits(reasons, SCC, SCC_TOTAL),
                'timeOfReport': timestamp(closed),
                'timeUsage': used,
                'datavolumeFBCUplink': self.rng.randrange(1_000, 2_000_000),
                'datavolumeFBCDownlink': self.rng.randrange(10_000, 50_000_000),
            }
            if not self._omit():
                container['timeOfFirstUsage'] = timestamp(opened)
                container['timeOfLastUsage'] = timestamp(opened + timedelta(seconds=used))
            if not self._omit():
                container['serviceIdentifier'] = group * 100 + 1
            containers.append(container)
        return containers

    def call(self, msisdn, imsi, start, direction):
        self.call_reference += 1
        other = self._other_party()
        duration = self.rng.randrange(5, 1200)
        record = {
            'recordType': 0 if direction == 'mo' else 1,
            'servedIMSI': tbcd(imsi),
            'recordingEntity': self._msc(),
            'answerTime': timestamp(start),
            'callDuration': duration,
            'causeForTerm': self.rng.choice(CALL_CAUSES),
            'callReference': self.call_reference.to_bytes(4, 'big'),
        }
        if direction == 'mo':
            record['servedMSISDN'] = address(msisdn)
            if not self._omit():
                record['callingNumber'] = address(msisdn)
            record['calledNumber'] = address(other)
            if not self._omit():
                record['serviceKey'] = 2
                record['levelOfCAMELService'] = bits(['basic', 'callDurSupervision'], CAMEL, CAMEL_TOTAL)
        else:
            record['servedMSISDN'] = address(msisdn)
            if not self._omit():
                record['callingNumber'] = address(other)
            if not self._omit():
                record['serviceKey'] = 2
        if not self._omit():
            record['location'] = self._location()
        return ('moCall' if direction == 'mo' else 'mtCall', record)

    def sms(self, msisdn, imsi, at, direction):
        self.message_reference = (self.message_reference + 1) % 256
        common = {
            'servedIMSI': tbcd(imsi),
            'msClassmark': b'\x33',
            'serviceCentre': address('62816124'),
            'recordingEntity': self._msc(),
        }
        if not self._omit():
            common['servedMSISDN'] = address(msisdn)
        if not self._omit():
            common['location'] = self._location()
        if not self._omit():
            common['smsResult'] = 0
        if not self._omit():
            common['cAMELSMSInformation'] = {'serviceKey': 3}
        if direction == 'mo':
            record = {
                'recordType': 6,
                'messageReference': bytes([self.message_reference]),
                'originationTime': timestamp(at),
                **common,
            }
            if not self._omit():
                record['destinationNumber'] = address(self._other_party())
            return ('moSMS', record)
        record = {'recordType': 7, 'deliveryTime': timestamp(at), **common}
        return ('mtSMS', record)
