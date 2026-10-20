"""Settings values shared by the main window and settings dialog."""
DEFAULTS={'alert_volume':50,'alert_sound':'standard','keep_band':True,'keep_mode':True,'auto_rst':True,'confirm_record':True,
          'location_assist':True,'monthly_backup':True,'backup_keep':30,
          'radio_enabled':False,'radio_model':'','radio_method':'CI-V','radio_port':'AUTO','radio_baud':'AUTO',
          'radio_civ_address':'94','radio_hamlib_model':'','radio_hamlib_path':'',
          'radio_virtual_enabled':False,'radio_setupc_path':'',
          'radio_autoset_rmks1':False,'radio_autoset_rmks2':False,'radio_autoset_band':False}

_BAUDS=(1200,2400,4800,9600,19200,38400,57600,115200)

def validate(values):
    result=dict(values)
    for key,default in DEFAULTS.items():
        value=result.get(key,default)
        if key=='alert_volume':
            if type(value) is not int or not 0<=value<=100:raise ValueError('通知音量は0〜100で指定してください。')
        elif key=='alert_sound':
            if value not in ('standard','terere'):raise ValueError('通知音の種類が不正です。')
        elif key=='backup_keep':
            if type(value) is not int or value not in (10,30,60,100):raise ValueError('バックアップ保持数は10・30・60・100から選択してください。')
        elif key in ('radio_model','radio_method','radio_port','radio_civ_address','radio_hamlib_model','radio_hamlib_path','radio_setupc_path'):
            if not isinstance(value,str):raise ValueError(key+'の設定値が不正です。')
        elif key=='radio_baud':
            if value!='AUTO' and (type(value) is not int or value not in _BAUDS):raise ValueError('無線機の通信速度が不正です。')
        elif type(value) is not bool:raise ValueError(key+'の設定値が不正です。')
        result[key]=value
    if result['radio_method'] not in ('CI-V','Hamlib'):raise ValueError('無線機の接続方式が不正です。')
    result['radio_port']=result['radio_port'].strip() or 'AUTO'
    if result['radio_civ_address'] and not __import__('re').fullmatch(r'[0-9A-Fa-f]{2}',result['radio_civ_address'].strip()):raise ValueError('CI-Vアドレスは16進数2桁で入力してください。')
    for key in ('band','mode','my_qth'):
        if key in result and not isinstance(result[key],str):raise ValueError(key+'の最新値は文字列です。')
    return result
