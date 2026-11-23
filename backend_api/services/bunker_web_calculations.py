"""Web-only deterministic calculation contract; does not modify desktop behavior.

The thermal correction below is the existing SOM formula, not a claim of
equivalence to ASTM/API petroleum tables. Volumes must already be corrected
using the vessel's tables; sounding, trim and heel cannot supply that volume
without the vessel-specific calibration data.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re

MAX_TANKS = 20
FUELS = ('vlsfo', 'mgo')
INPUTS = ('name', 'dist_mtrs', 'gauge_mtrs', 'volume_m3', 'temp_c', 'density_15c')
MODEL = 'som-thermal-0.00063-excel-round-v1'


def number(value, field):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError(f'{field}: a numeric value is required')
    raw = str(value).strip().replace('\u00a0', '').replace(' ', '')
    if ',' in raw and '.' in raw:
        if raw.rfind(',') > raw.rfind('.'):
            if not re.fullmatch(r'[+-]?\d{1,3}(?:\.\d{3})+,\d+', raw):
                raise ValueError(f'{field}: invalid numeric separators')
            raw = raw.replace('.', '').replace(',', '.')
        else:
            if not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+\.\d+', raw):
                raise ValueError(f'{field}: invalid numeric separators')
            raw = raw.replace(',', '')
    else:
        raw = raw.replace(',', '.')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', raw) or len(raw) > 30:
        raise ValueError(f'{field}: invalid decimal number')
    try:
        result = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f'{field}: invalid decimal number') from exc
    if not result.is_finite() or abs(result) >= Decimal('1e15'):
        raise ValueError(f'{field}: number out of supported range')
    return result


def rounded(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate(payload):
    """Recompute, ignoring submitted derived values; incomplete tanks fail closed.

Returns strings so JSON clients never introduce binary-float recalculation.
Explicit zero is retained; missing values are never treated as zero.
"""
    totals = {fuel: Decimal(0) for fuel in FUELS}
    tanks, normalized, errors = [], {}, []
    for key in payload:
        match = re.match(r'^(vlsfo|mgo)_tank_(\d+)_', key)
        if match and not 1 <= int(match[2]) <= MAX_TANKS:
            errors.append(f'{key}: tank index must be between 1 and {MAX_TANKS}')
    with localcontext() as context:
        context.prec = 50
        for fuel in FUELS:
            for index in range(1, MAX_TANKS + 1):
                prefix = f'{fuel}_tank_{index}_'
                raw = {key: payload.get(prefix + key) for key in INPUTS}
                present = any(v is not None and str(v).strip() for v in raw.values())
                normalized[prefix+'temp_f'] = None
                normalized[prefix+'weight_mt'] = None
                if not present:
                    continue
                row = dict(fuel=fuel, index=index, name=str(raw['name'] or ''),
                           temp_f=None, weight_mt=None)
                tanks.append(row)
                try:
                    volume_empty = str(raw['volume_m3'] or '').strip().upper() == 'EMPTY'
                    vol = None if volume_empty else number(raw['volume_m3'], prefix+'volume_m3')
                    temp = number(raw['temp_c'], prefix+'temp_c')
                    density = number(raw['density_15c'], prefix+'density_15c')
                    for key, value in (('volume_m3', vol), ('temp_c', temp), ('density_15c', density)):
                        normalized[prefix+key] = str(value) if value is not None else None
                    if volume_empty:normalized[prefix+'volume_m3']='EMPTY'
                    if temp is not None:
                        row['temp_f'] = str(rounded(temp * Decimal('1.8') + Decimal(32)))
                        normalized[prefix+'temp_f'] = row['temp_f']
                    declared_empty = vol in (None,Decimal(0)) and (volume_empty or str(raw['gauge_mtrs'] or '').strip().upper()=='EMPTY')
                    if declared_empty:
                        row['empty']=True
                        row['weight_mt']='0.00'
                        normalized[prefix+'weight_mt']='0.00'
                        continue
                    if any(value is None for value in (vol, temp, density)):
                        raise ValueError(f'{prefix}volume/temp/density: complete all three measurements')
                    if vol < 0 or not Decimal(0)<density<Decimal(2):
                        raise ValueError(f'{prefix}volume must be nonnegative; density must be in t/m3 (between 0 and 2), not kg/m3')
                    if temp < Decimal('-273.15'):
                        raise ValueError(f'{prefix}temperature is below absolute zero; verify units')
                    corrected = density - Decimal('0.00063') * (temp - Decimal(15))
                    if corrected <= 0:
                        raise ValueError(f'{prefix}corrected density must be positive; verify units')
                    weight = rounded(vol * corrected)
                    row['weight_mt'] = str(weight)
                    normalized[prefix+'weight_mt'] = str(weight)
                    totals[fuel] += weight
                except ValueError as exc:
                    errors.append(str(exc))
        # A partially calculated total must never look like a final ROB.
        result_totals = None if errors else {fuel: str(rounded(total)) for fuel, total in totals.items()}
        grand = None if errors else str(rounded(sum(totals.values())))
    # UNITED HARMONY reference: ROB + Generator until DLOSP + Departure M.E.
    # These occupy figure slots 2 and 3. Do not sum unrelated/custom figures.
    dlosp={}
    for fuel,suffix in (('vlsfo','vlsfo'),('mgo','lsmgo')):
        try:
            adjustments=[number(payload.get(f'bunker_figure_{i}_{suffix}'),f'bunker_figure_{i}_{suffix}') for i in (2,3)]
            dlosp[fuel]=str(rounded(totals[fuel]+sum(v for v in adjustments if v is not None))) if not errors and any(v is not None for v in adjustments) else None
            if dlosp[fuel] is not None and Decimal(dlosp[fuel])<0:
                raise ValueError(f'{fuel}: DLOSP cannot be negative; verify signed adjustments')
        except ValueError as exc:
            errors.append(str(exc));dlosp[fuel]=None
    if errors:result_totals=grand=None;dlosp={fuel:None for fuel in FUELS}
    return dict(model=MODEL, tanks=tanks, fields=normalized, errors=errors,
                valid=not errors, totals=result_totals, total_mt=grand,dlosp=dlosp)
