"""Settings values shared by the main window and settings dialog."""
DEFAULTS={'keep_band':True,'keep_mode':True,'auto_rst':True,'confirm_record':True,
          'location_assist':True,'monthly_backup':True,'backup_keep':30}
def validate(values):
    result=dict(values)
    for key,default in DEFAULTS.items():
        value=result.get(key,default)
        if key=='backup_keep':
            if type(value) is not int or value not in (10,30,60,100):raise ValueError('バックアップ保持数は10・30・60・100から選択してください。')
        elif type(value) is not bool:raise ValueError(key+'の設定値が不正です。')
        result[key]=value
    for key in ('band','mode','my_qth'):
        if key in result and not isinstance(result[key],str):raise ValueError(key+'の最新値は文字列です。')
    return result
