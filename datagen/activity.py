def usage(ledger, sessions, msisdn, imsi, at, kind, direction='mo'):
    if not ledger.is_active(msisdn):
        return []
    if kind == 'data':
        return sessions.data_session(msisdn, imsi, at)
    if kind == 'call':
        return [sessions.call(msisdn, imsi, at, direction)]
    if kind == 'sms':
        return [sessions.sms(msisdn, imsi, at, direction)]
    raise ValueError(f'unknown usage kind {kind!r}')
