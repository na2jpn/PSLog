"""Power ceilings selected by an explicit declaration of operating circumstances."""
import math

def validate(spec):
    from contest_rules import keys,number
    keys(spec,('stationary','portable'),'運用形態別電力')
    for value in spec.values():
        if value is None:continue
        number(value,'運用形態別の最大電力')
        if value<=0:raise ValueError('運用形態別電力は0より大きい値です。')

def check(event,context):
    spec=event.get('power_by_operation')
    if not spec:return None
    kind=context.get('operation_kind')
    if kind not in spec:raise ValueError('移動しない運用／移動運用を明示的に選択してください。')
    power=context.get('power')
    if type(power) not in (int,float) or not math.isfinite(power) or not (power>0 and (spec[kind] is None or power<=spec[kind])):raise ValueError(('移動運用' if kind=='portable' else '移動しない運用')+f'の最大電力は{spec[kind]}W以内です。')
    return spec[kind]

def check_submission(event,context,info,own):
    import re
    if not event.get('power_by_operation'):return
    check(event,context)
    moving=context['operation_kind']=='portable'
    if type(info.get('portable',False)) is not bool or info.get('portable',False)!=moving:raise ValueError('提出の移動指定と、電力条件で申告した運用形態が一致しません。')
    if not moving and re.search(r'/(?:[0-9]|P|JD1)$',own.upper()):raise ValueError('自局コールに移動表記があります。運用形態の申告と使用ログを確認してください。')
    if moving and not str(info.get('opplace','')).strip():raise ValueError('移動運用の具体的な運用地を入力してください。')
