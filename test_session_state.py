import unittest,tempfile
from datetime import datetime
from storage import Repository,save_settings,load_settings
from session_state import (MAX_STANDARD,MAX_CONTEST,CONTEST_PALETTE,clean_contest_name,
    clean_event_ym,contest_suffix,standard_session,contest_session,restore,next_standard_slot,
    contest_colors,session_title,recent_snapshot,reopen_snapshot)

class SessionStateTests(unittest.TestCase):
    def test_names_and_suffix(self):
        self.assertEqual(clean_contest_name('aadx'),'AADX')
        self.assertEqual(clean_event_ym('202609'),'202609')
        self.assertEqual(contest_suffix('aadx','202609'),'AADX202609')
        with tempfile.TemporaryDirectory() as tmp:
            path=Repository(tmp).path_for('JH1HST',contest_suffix('aadx','202609'),'2026-09-16')
            self.assertEqual(path.name,'2026_JH1HST_AADX202609.txt')
        with self.assertRaises(ValueError):clean_contest_name('AADX-SSB')
        with self.assertRaises(ValueError):clean_event_ym('202613')
    def test_legacy_settings_become_one_standard(self):
        sessions,index,recent=restore({'own':'JH1HST','band':'50','mode':'CW'},datetime(2026,9,16))
        self.assertEqual(len(sessions),1);self.assertEqual(index,0);self.assertFalse(recent)
        self.assertEqual(sessions[0]['type'],'standard');self.assertEqual(sessions[0]['call'],'JH1HST')
        self.assertEqual(sessions[0]['band'],'50');self.assertEqual(session_title(sessions[0]),'[A]JH1HST')
    def test_standard_title_uses_call_suffix_and_empty_fallback(self):
        plain=standard_session(1,{'own':'JH1HST'})
        suffixed=standard_session(2,{'own':'JH1HST','suffix':'JP1220'})
        empty=standard_session(3,{'own':'','suffix':'JP1220'})
        self.assertEqual(session_title(plain),'[A]JH1HST')
        self.assertEqual(session_title(suffixed),'[A]JH1HST-JP1220')
        self.assertEqual(session_title(empty),'[A]標準')
        # Slot is internal only; duplicate visible titles remain allowed.
        duplicate=standard_session(4,{'own':'JH1HST'})
        self.assertEqual(session_title(duplicate),session_title(plain))

    def test_limits_duplicate_ids_and_self_repair(self):
        raw=[]
        for i in range(8):
            s=standard_session((i%5)+1,{'own':'JH1HST'});s['id']='same';raw.append(s)
        for i in range(9):raw.append(contest_session('C'+str(i),'202609','JH1HST'))
        sessions,index,_=restore({'workspace_sessions':raw},datetime(2026,9,16))
        self.assertLessEqual(sum(s['type']=='standard' for s in sessions),MAX_STANDARD)
        self.assertLessEqual(sum(s['type']=='contest' for s in sessions),MAX_CONTEST)
        self.assertEqual(len({s['id'] for s in sessions}),len(sessions))
        repaired,_,_=restore({'workspace_sessions':[{'type':'broken'}]},datetime(2026,9,16))
        self.assertEqual(len(repaired),1);self.assertEqual(repaired[0]['type'],'standard')
    def test_slots_and_colors_are_display_only(self):
        sessions=[standard_session(1)]
        self.assertEqual(next_standard_slot(sessions),2)
        sessions += [contest_session('AADX','202609'),contest_session('JA0','202609')]
        colors=contest_colors(sessions)
        self.assertEqual(colors[sessions[1]['id']]['name'],CONTEST_PALETTE[0]['name'])
        self.assertEqual(colors[sessions[2]['id']]['name'],CONTEST_PALETTE[1]['name'])
        self.assertNotIn('color',sessions[1])

    def test_active_and_recent_restore(self):
        first=standard_session(1,{'own':'JH1HST'});second=contest_session('AADX','202609','JH1HST')
        recent=contest_session('JA0','202609','JH1HST')
        sessions,index,closed=restore({'workspace_sessions':[first,second],'active_workspace_id':second['id'],
            'recent_workspace_sessions':[recent]},datetime(2026,9,16))
        self.assertEqual(index,1);self.assertEqual(sessions[index]['contest_name'],'AADX')
        self.assertEqual(len(closed),1);self.assertEqual(closed[0]['contest_name'],'JA0')


    def test_recent_tab_snapshot_and_reopen_preserve_own_callsign(self):
        tab=standard_session(2,{'own':'JQ7FIU','band':'430','mode':'FM'})
        snap=recent_snapshot(tab,'JH1HST')
        self.assertEqual(snap['call'],'JQ7FIU')
        reopened=reopen_snapshot(snap,'JH1HST')
        self.assertEqual(reopened['call'],'JQ7FIU')
        # Legacy/partial recent history with no per-tab call falls back safely,
        # but a real saved per-tab call always wins over that fallback.
        legacy=dict(snap);legacy['call']=''
        self.assertEqual(reopen_snapshot(legacy,'JH1HST')['call'],'JH1HST')

    def test_workspace_state_roundtrip_through_conf(self):
        standard=standard_session(1,{'own':'JH1HST','band':'7','mode':'CW'});contest=contest_session('AADX','202609','JH1HST','14','CW','Japan')
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'workspace_sessions':[standard,contest],'active_workspace_id':contest['id']})
            loaded=load_settings(tmp);sessions,index,_=restore(loaded,datetime(2026,9,16))
            self.assertEqual([s['type'] for s in sessions],['standard','contest']);self.assertEqual(index,1)
            self.assertEqual(sessions[1]['contest_name'],'AADX');self.assertEqual(sessions[1]['my_qth'],'Japan')

if __name__=='__main__':unittest.main()
