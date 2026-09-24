"""Explicit name equivalences; no general fuzzy matching or current-name replacement."""
ALIASES={
'神奈川県横浜市保土ヶ谷区':'神奈川県横浜市保土ケ谷区',
'千葉県袖ヶ浦市':'千葉県袖ケ浦市','茨城県龍ヶ崎市':'茨城県龍ケ崎市',
'岩手県胆沢郡金ヶ崎町':'岩手県胆沢郡金ケ崎町','岐阜県不破郡関ヶ原町':'岐阜県不破郡関ケ原町',
'福岡県糟屋郡須恵町':'福岡県糟屋郡須惠町','福岡県三瀦郡大木町':'福岡県三潴郡大木町',
'東京都大島支庁大島町':'東京都大島町','東京都大島支庁利島村':'東京都利島村',
'東京都大島支庁新島村':'東京都新島村','東京都大島支庁神津島村':'東京都神津島村',
'東京都三宅支庁三宅村':'東京都三宅島三宅村','東京都三宅支庁御蔵島村':'東京都御蔵島村',
'東京都八丈支庁八丈町':'東京都八丈島八丈町','東京都八丈支庁青ヶ島村':'東京都青ヶ島村',
'東京都小笠原支庁小笠原村':'東京都小笠原村',
}
# The official file truncates roman municipality fields at 35 characters.
# Only suffix fragments are removed; no missing place-name letters are inferred.
TRUNCATED={
'HIGASHISHIRAKAWA GUN YAMATSURI MACH':'Yamatsuri Higashishirakawa gun',
'NISHIYATSUSHIRO GUN ICHIKAWAMISATO':'Ichikawamisato Nishiyatsushiro gun',
'MINAMITSURU GUN FUJIKAWAGUCHIKO MAC':'Fujikawaguchiko Minamitsuru gun',
'MINAMIKAWACHI GUN CHIHAYAAKASAKA MU':'Chihayaakasaka Minamikawachi gun',
}
PARENT_CITIES={'千葉県千葉市':('千葉県千葉市','CHIBA SHI'),
               '埼玉県さいたま市':('埼玉県さいたま市','SAITAMA SHI')}

# PHP master names/codes remain authoritative. These are PSLog transliterations,
# not claims that the current postal dataset contains the historical entries.
HISTORICAL_QTH={
('180201','静岡県浜松市中区'):'Naka Hamamatsu Shizuoka Japan',
('180202','静岡県浜松市東区'):'Higashi Hamamatsu Shizuoka Japan',
('180203','静岡県浜松市西区'):'Nishi Hamamatsu Shizuoka Japan',
('180204','静岡県浜松市南区'):'Minami Hamamatsu Shizuoka Japan',
('180205','静岡県浜松市北区'):'Kita Hamamatsu Shizuoka Japan',
('180206','静岡県浜松市浜北区'):'Hamakita Hamamatsu Shizuoka Japan',
('2722','兵庫県篠山市'):'Sasayama Hyogo Japan',
('40010B','福岡県筑紫郡那珂川町'):'Nakagawa Chikushi gun Fukuoka Japan',
}
