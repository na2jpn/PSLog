"""Supported mappings verified against ADIF 3.1.7 (not its full enumeration)."""
ADIF_VERSION='3.1.7'
MODES={m:(m,'') for m in ('AM','CW','FM','SSB','RTTY','SSTV','FT8','JT65','JT9','PSK','MFSK','DIGITALVOICE','MSK144','OLIVIA','WSPR','DYNAMIC')}
for parent,children in {
    'MFSK':'FT2,FT4,JS8,Q65,FST4,FST4W',
    'DIGITALVOICE':'FREEDV,C4FM,DSTAR,DMR,M17',
    'SSB':'USB,LSB',
    'PSK':'PSK31,PSK63,PSK125',
    'JT65':'JT65A,JT65B,JT65B2,JT65C,JT65C2',
    'DYNAMIC':'FREEDATA,VARA HF,VARA SATELLITE,VARA FM 1200,VARA FM 9600',
}.items():
    for child in children.split(','):MODES[child]=(parent,child)


def mapping(value):
    key=value.strip().upper()
    if key in MODES:return MODES[key]
    # Preserve the approved substring matching for local FT/FreeDV labels.
    # Multiple known families in one label remain ambiguous and are rejected.
    candidates={MODES[base] for base in ('FT8','FT4','FT2','FREEDV') if base in key}
    if len(candidates)>1:return None
    if len(candidates)==1:return next(iter(candidates))
    # PSLog may append a local qualifier after a known mode (e.g. VARA HF AS).
    # Map the longest known leading mode while APP_PSLOG_MODE preserves the
    # complete original string for a lossless PSLog -> ADIF -> PSLog round trip.
    prefixes=[name for name in MODES if key.startswith(name+' ')]
    if prefixes:
        return MODES[max(prefixes,key=len)]
    return None


def check_pair(mode,submode):
    """Reject known contradictions; future names remain acceptable input."""
    parent=MODES.get(mode.upper())
    child=MODES.get(submode.upper())
    if mode and submode and parent and child:
        if not child[1] or parent[0]!=child[0] or (parent[1] and parent[1]!=child[1]):
            raise ValueError('MODEとSUBMODEの組み合わせが一致しません: '+mode+' / '+submode)
