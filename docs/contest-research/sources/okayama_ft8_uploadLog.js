/**
 * ログアップローダー　JavaScriptファイル
 * @author JJ4KME
 */
const METHOD_TYPE			= 'POST';
const DATA_TYPE				= 'json';
const URL_AJAX				= 'uploadLog.php';
const regClubnumberChar		= /^[a-hA-H0-9\-]$/;
const regClubnumberFormat	= /^(\d{2}[a-hA-H]?)\-([1-5])\-(\d{1,4})$/;
const regDateChar			= /^[\d\/]$/;
const regDateFormat1		= /^((\d{4})(\/))?(\d{1,2})\/(\d{1,2})$/;
const regDateFormat2		= /^(\d{4})?(\d{2})(\d{2})$/;
const regTimeChar			= /^[\d:]$/;
const regTimeFormat1		= /^(\d{1,2}):(\d{1,2})$/;
const regTimeFormat2		= /^(\d{2})(\d{2})$/;
const regCallsignChar		= /^[a-zA-Z0-9\/]$/;
const regCallsign			= /^[a-zA-Z0-9]+(\/[a-zA-Z0-9]+)?$/;
const regSWLChar			= /^[a-zA-Z0-9\/\-]$/;
const regSWL				= /^JA[0-9]\-\d+(\/.+)?$/;
const regRstChar			= /^[1-9]$/;
const regRstFormat			= /^[1-5][1-9][1-9]?$/;
const regMultiChar			= /^[\da-zA-Z\-\/]$/;
const regMultiFormat		= /^([\da-zA-Z\/]{2,6}|\-)$/;
let contest_id;
let contest;
let category				= null;
let bands;
let reg_clubs;

/**
 * 読み込み完了後の処理
 * @param e イベント
 */
$(window).on('load', function(e) {

	let temp = location.search.substr(1).split('&');
	contest_id	= temp[0];
	if (temp.length > 1) {
		category = temp[1];
	}

	// ＪＡＲＬ形式でファイルをアップロード
	$('button#jarl_file').click(function(e) {
		$('form#import input#contest_id').val(contest_id);
		$('form#import td#fileType').html('ＪＡＲＬ形式');
		$('form#import input#fileType').val('jarl');
		$('form#import input#method').val('file');
		$('form#import tr#file').show();
		$('form#import tr#text').hide();
		$('form#import input#source').val('');
		$('form#import input#timezone_jst').prop('checked', true);

		$('div#import').modal('show');
	});

	// ＪＡＲＬ形式でテキスト貼り付け
	$('button#jarl_text').click(function(e) {
		$('form#import input#contest_id').val(contest_id);
		$('form#import td#fileType').html('ＪＡＲＬ形式');
		$('form#import input#fileType').val('jarl');
		$('form#import input#method').val('text');
		$('form#import tr#file').hide();
		$('form#import tr#text').show();
		$('form#import textarea#source').val('');
		$('form#import input#timezone_jst').prop('checked', true);

		$('div#import').modal('show');
	});

	// Cabrillo形式でファイルをアップロード
	$('button#cabrillo_file').click(function(e) {
		$('form#import input#contest_id').val(contest_id);
		$('form#import td#fileType').html('Cabrillo形式');
		$('form#import input#fileType').val('cabrillo');
		$('form#import input#method').val('file');
		$('form#import tr#file').show();
		$('form#import tr#text').hide();
		$('form#import input#source').val('');
		$('form#import input#timezone_utc').prop('checked', true);

		$('div#import').modal('show');
	});

	// Cabrillo形式でテキスト貼り付け
	$('button#cabrillo_text').click(function(e) {
		$('form#import input#contest_id').val(contest_id);
		$('form#import td#fileType').html('Cabrillo形式');
		$('form#import input#fileType').val('cabrillo');
		$('form#import input#method').val('text');
		$('form#import tr#file').hide();
		$('form#import tr#text').show();
		$('form#import textarea#source').val('');
		$('form#import input#timezone_utc').prop('checked', true);

		$('div#import').modal('show');
	});

	$('button#import_start').click(function(e) {

		if ($('input#method').val() == 'file' && $('input#source').val() == '') {
			// ファイルが未選択
			$('input#source').focus();
			showAlertDialog(contest.contest_name, 'アップロードするファイルを選択してください');
			return;
		}

		if ($('input#method').val() == 'text' && $('textarea#source').val() == '') {
			// テキストが未入力
			$('textarea#source').focus();
			showAlertDialog(contest.contest_name, 'サマリーとログを貼り付けてください');
			return;
		}

		importLog(new FormData($('form#import')[0]));
		$('div#import').modal('hide');
	});
	$('button#import_cancel').click(function(e) {

		$('div#import').modal('hide');
	});

	// 提出ボタンが押された
	$('button#register').click(function(e) {
		if ($('select#category').prop('selectedIndex') == -1) {
			// カテゴリーが未選択
			$('select#category').focus();
			showAlertDialog(contest.contest_name, '参加部門を選択してください');
			return;
		}

		if ($('input#owner').val() == '') {
			// コールサインが未入力
			$('input#owner').focus();
			showAlertDialog(contest.contest_name, '運用したコールサインを入力してください');
			return;

		} else if (!$('input#owner').val().match(regCallsign) && !$('input#owner').val().match(regSWL)) {
			// 形式が合っていなかったら
			$('input#owner').focus();
			showAlertDialog(contest.contest_name, 'コールサインのフォーマットが不正です');
			return;
		}

		if ($('input#name').val() == '') {
			// 氏名が未入力
			$('input#name').focus();
			showAlertDialog(contest.contest_name, '氏名(社団の代表者名)を入力してください');
			return;
		}

		if ($('form#register input#password1').val() != $('form#register input#password2').val()) {
			// パスワードが違う
			showAlertDialog(contest.contest_name, 'パスワードが異なります');
			return;
		}

//		if (countLog() == 0 && $('td#logType').html() != 'その他') {
//			// ログが無い
//			showAlertDialog(contest.contest_name, 'ログデータが入力されていません');
//			return;
//		}

		if ($('input#replaceLog').is(':visible') && !$('input#replaceLog').prop('checked')) {
			// ログ置換チェックが入っていない
			showAlertDialog(contest.contest_name, '既に提出済みのサマリーが削除されます。確認のためチェックを入れてください');
			return;
		}

		$('form#register input#contest_id').val(contest_id);

		registerLog(new FormData($('form#register')[0]));
	});

	new bootstrap.Modal('div#import');
	initialize();
});

/**
 * 初期処理
 */
function initialize() {

	$.ajax({
		type:		METHOD_TYPE,
		url:		URL_AJAX,
		dataType:	DATA_TYPE,
		data:		{
			CALL_AJAX:	'initialize',
			contest_id:	contest_id},
		beforeSend:	function (jqXHR) {
			$('div#wait').show();
		}
	}).done(function (data, textStatus, jqXHR) {
		if (data.success) {
			// 正常に取得できていたら
			// コンテスト名をセット
			contest = data.contest;
			document.title = data.contest.contest_name + ' ログアップロード';
			$('span#contest_name').html(data.contest.contest_name);
			// 主催者名をセット
			$('span#organizer_name').html(data.contest.organizer_name);
			// ステータスに合わせてメッセージを表示
			if (data.status == 0) {
				$('p#message').append(
					data.contest.contest_name + 'はまだ開催されていません。お試しでログのアップロードは可能ですが、コンテスト開始時にデータは抹消されます',
					$('<br />'),
					'ログ提出システムに関してご意見等あれば ' + data.contest.organizer_name + ' まで連絡頂ければ幸いです');

			} else if (data.status == 1) {
				$('p#message').html(data.contest.contest_name + 'は現在開催中です。お早めにログの提出をお願いします');

			} else if (data.status == 2) {
				$('p#message').html(data.contest.contest_name + 'は終了しました。お早めにログの提出をお願いします');

			} else if (data.status == 3) {
				$('p#message').html('ただいまの期間は電子データでのチェックログのみ受け付けています');

			} else if (data.status == 4) {
				$('body').empty();
				$('body').append(
					$('<p />').attr({id: 'message'}).html(data.contest.contest_name + 'はログの提出を締め切りました。結果発表までしばらくお待ちください'));
			}

			// 登録クラブ対抗ありだったら表示
			if (data.contest.use_regclub) {
				$('div#box_regclub').removeClass('d-none');
			}

			// 成績閲覧用パスワード使用ありだったら表示
			if (data.contest.use_password) {
				$('div#box_password').removeClass('d-none');
			}

			// 周波数帯のリストをセット
			bands = data.bands;
			$('select#freq').empty();
			for (let value in data.bands) {
				$('select#freq').append($('<option />').val(value).html(data.bands[value]));
			}
			$('select#freq').prop('selectedIndex', -1);
			$('table#score > tbody').empty();
			for (let value in data.bands) {
				$('table#score > tbody').append($('<tr />').append([
					$('<th />').addClass('fs-6 band').html(data.bands[value] + ' MHz'),
					$('<td />').addClass('fs-6 numqso').attr({id: 'numqso_' + value}),
					$('<td />').addClass('fs-6 point' ).attr({id: 'point_'  + value}),
					$('<td />').addClass('fs-6 multi' ).attr({id: 'multi_'  + value}),
					$('<td />').addClass('fs-6 score' ).attr({id: 'score_'  + value})]));
			}

			// モードのリストをセット
			$('select#mode').empty();
			for (let i = 0; i < data.MODES.length; i++) {
				$('select#mode').append($('<option />').val(data.MODES[i].category).html(data.MODES[i].disp_name));
			}
			$('select#mode').prop('selectedIndex', -1);

			// 参加部門のリストをセット
			$('select#category').empty();
			for (let i = 0; i < data.CATEGORIES.length; i++) {
				$('select#category').append($('<option />').val(data.CATEGORIES[i].code).html(data.CATEGORIES[i].name));
			}
			if (category === null) {
				$('select#category').prop('selectedIndex', -1);
			} else {
				$('select#category').val(category);
			}

			// 登録クラブのリストを保存
			reg_clubs = {};
			for (let i = 0; i < data.CLUBS.length; i++) {
				reg_clubs[[data.CLUBS[i].shibu, data.CLUBS[i].genre, String(data.CLUBS[i].number).padStart(4, '0')].join('-')] = data.CLUBS[i].name;
			}
		}

	}).fail(function (jqXHR, textStatus, errorThrown) {

	}).always(function () {
		$('div#wait').hide();
	});
}

/**
 * ログを追加できるか調べる
 * @returns 追加ＯＫならtrue、ＮＧならfalse
 */
function canRegist() {

	let source1 = $('table#log > tfoot > tr#input').find('input');
	let source2 = $('table#log > tfoot > tr#input').find('select');

	let valid	= 0;
	for (let i = 0; i < source1.length; i++) {
//		if ($(source1[i]).hasClass('is-valid')) {
		if (!$(source1[i]).hasClass('is-invalid')) {
			valid++;
		}
	}

	for (let i = 0; i < source2.length; i++) {
//		if ($(source2[i]).hasClass('is-valid')) {
		if (!$(source2[i]).hasClass('is-invalid')) {
			valid++;
		}
	}

	$('table#log > tfoot > tr#input').find('button').prop('disabled', (source1.length + source2.length != valid));
	return (source1.length + source2.length == valid);
}

/**
 * 参加部門コードからフォーカスが外れた
 * @param target 対象要素
 */
const onBlur_CategoryCode = (target) => {

	$(target).removeClass('is-valid is-invalid').val(target.value.toUpperCase());

	if ($('select#category').find('[value=' + target.value + ']').length > 0) {
		// カテゴリーコードが見つかったら
		$('select#category').val(target.value);
		$(target).addClass('is-valid');

	} else {
		// カテゴリーコードが見つからなかったら
		$(target).addClass('is-invalid');
		$(target).find('~ div.invalid-tooltip').html('指定されたカテゴリーコードは存在しません');
	}
};

/**
 * 参加部門名称が変更された
 * @param target 対象要素
 */
const onChange_CategoryName = (target) => {

	$('input#category-code').addClass('is-valid').val($(target).val());
};

/**
 * コールサインでキーが押された
 * @param e イベント
 * @returns 入力ＯＫならtrue、ＮＧならfalse
 */
function onKeyPress_Owner(e) {

	return	regCallsignChar.test(e.key) || regSWLChar.test(e.key);
}

/**
 * コールサインからフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Owner(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid').prop('title', '');

	if (value == '') {
		// コールサインが入力されていなかったら
		$(target).addClass('is-invalid').prop('title', 'コールサインを入力してください');
		$(target).find('~ div.invalid-tooltip').html('コールサインを入力してください');

	} else if (!value.match(regCallsign) && !value.match(regSWL)) {
		// 形式が合っていなかったら
		$(target).addClass('is-invalid').prop('title', 'コールサインのフォーマットが不正です');
		$(target).find('~ div.invalid-tooltip').html('コールサインのフォーマットが不正です');

	} else {
		$(target).addClass('is-valid').val(value.toUpperCase());
	}
}

/**
 * 氏名(社団名)からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Name(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid').prop('title', '');

	if (value == '') {
		// 氏名(社団名)が入力されていなかったら
		$(target).addClass('is-invalid').prop('title', '氏名(社団名)を入力してください');
		$(target).find('~ div.invalid-tooltip').html('氏名(社団名)を入力してください');

	} else {
		$(target).addClass('is-valid');
	}
}

/**
 * 連絡先住所らフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Address(target) {

	$(target).removeClass('is-valid is-invalid');

	if ($(target).val() != '') {
		$(target).addClass('is-valid');
	}
}

/**
 * 登録クラブ番号でキーが押された
 * @param e イベント
 * @returns 入力ＯＫならtrue、ＮＧならfalse
 */
function onKeyPress_Regclubnumber(e) {

	return	regClubnumberChar.test(String.fromCharCode(e.which));
}

/**
 * 登録クラブ番号からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Regclubnumber(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid');

	if (value == '') {
		$('input#regclubname').val('');
		return;

	} else if (value.match(regClubnumberFormat)) {
		let temp = value.match(regClubnumberFormat);
		target.value = [temp[1].toUpperCase(), temp[2], String(parseInt(temp[3])).padStart(4, '0')].join('-');
		if (reg_clubs.hasOwnProperty(target.value)) {
			$('input#regclubname').val(reg_clubs[target.value]);

		} else {
			$('input#regclubname').val('');
		}

		$(target).addClass('is-valid');

	} else {
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('登録クラブ番号のフォーマットが不正です');
	}
}

/**
 * 日付からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Date(target) {

	let value = target.value;
	$(target).removeClass('is-invalid is-valid');

	if (value == '') {
		// 日付が指定されていなかったら
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('日付を入力してください');

	} else {
		$(target).addClass('is-valid');
	}

	canRegist();
}

/**
 * 時刻からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Time(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid');

	if (value == '') {
		// 時刻が指定されていなかったら
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('時刻を入力してください');

	} else {
		$(target).addClass('is-valid');
	}

	canRegist();
}

/**
 * コールサインでキーが押された
 * @param e イベント
 * @returns 入力ＯＫならtrue、ＮＧならfalse
 */
function onKeyPress_Callsign(e) {

	return	regCallsignChar.test(String.fromCharCode(e.which)) || regSWLChar.test(String.fromCharCode(e.which));
}

/**
 * コールサインからフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Callsign(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid');

	if (value == '') {
		// コールサインが入力されていなかったら
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('コールサインを入力してください');

	} else if (!value.match(regCallsign) && !value.match(regSWL)) {
		// 形式が合っていなかったら
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('コールサインのフォーマットが不正です');

	} else {
		$(target).addClass('is-valid').val(value.toUpperCase());
	}

	canRegist();
}

/**
 * 周波数からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Freq(target) {

	$(target).removeClass('is-valid is-invalid');

	let index = $(target).prop('selectedIndex');
	if (index == -1) {
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('周波数帯を選択してください');
		return;

	} else {
		$(target).addClass('is-valid');
	}
}

/**
 * 電波の型式からフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Mode(target) {

	$(target).removeClass('is-valid is-invalid');

	let index = $(target).prop('selectedIndex');
	if (index == -1) {
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('電波の型式を選択してください');
		return;

	} else {
		if (target.value == 'P') {
			$('input#sent_rst').val('59');
			$('input#recv_rst').val('59');

		} else {
			$('input#sent_rst').val('599');
			$('input#recv_rst').val('599');
		}

		$(target).addClass('is-valid');
	}
}

/**
 * リポートでキーが押された
 * @param e イベント
 * @returns 入力ＯＫならtrue、ＮＧならfalse
 */
function onKeyPress_Rst(e) {

	return	regRstChar.test(String.fromCharCode(e.which));
}

/**
 * リポートからフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Rst(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid');

//	if (value == '') {
//		// リポートが入力されていなかったら
//		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('リポートを入力してください');
//
//	} else {
		$(target).addClass('is-valid');
//	}

	canRegist();
}

/**
 * マルチプライヤーでキーが押された
 * @param e イベント
 * @returns 入力ＯＫならtrue、ＮＧならfalse
 */
function onKeyPress_Multi(e) {

	return	regMultiChar.test(String.fromCharCode(e.which));
}

/**
 * マルチプライヤーからフォーカスが外れた
 * @param target 対象要素
 */
function onBlur_Multi(target) {

	let value = target.value;
	$(target).removeClass('is-valid is-invalid');

	if (value == '') {
		// リポートが入力されていなかったら
		$(target).addClass('is-invalid').find('~ div.invalid-tooltip').html('マルチプライヤーを入力してください');

	} else {
		$(target).addClass('is-valid');
	}

	canRegist();
}

/**
 * ログを追加する
 * @param event イベント
 */
function addRow(event) {

	let target = $(event.target).parent().parent();

	if (!canRegist()) {
		return;
	}

	let freqIndex = $(target).find('select#freq').prop('selectedIndex');
	let modeIndex = $(target).find('select#mode').prop('selectedIndex');

	// １件のログデータを作る
	let newLine = getLogRow({
			workdate:	$(target).find('input#workdate').val(),
			worktime:	$(target).find('input#worktime').val(),
			callsign:	$(target).find('input#callsign').val().toUpperCase(),
			frequency:	$(target).find('select#freq > option')[freqIndex].value,
			band:		$(target).find('select#freq > option')[freqIndex].innerHTML,
			modecat:	$(target).find('select#mode > option')[modeIndex].value,
			mode:		$(target).find('select#mode > option')[modeIndex].innerHTML,
			sent_rst:	$(target).find('input#sent_rst').val(),
			sent_multi:	$(target).find('input#sent_multi').val(),
			recv_rst:	$(target).find('input#recv_rst').val(),
			recv_multi:	$(target).find('input#recv_multi').val()});
	// 削除ボタンを付ける
	$(newLine).append($('<td />').addClass('p-0 button').append($('<button />').addClass('btn btn-sm btn-primary').attr({onclick: 'deleteRow(event);'}).html('←削除')));

	$('table#log > tbody').append(newLine);

	$(target).find('input#worktime'  ).removeClass('is-valid is-invalid').val('');
	$(target).find('input#callsign'  ).removeClass('is-valid is-invalid').val('');
	$(target).find('input#recv_rst'  ).removeClass('is-valid is-invalid').val('');
	$(target).find('input#recv_multi').removeClass('is-valid is-invalid').val('');
	$(target).find('button').prop('disabled', true);

	$('td#logCount').html(countLog());
}

/**
 * ログを削除する
 * @param e イベント
 */
function deleteRow(e) {

	$(e.target).parent().parent().remove();
	$('td#logCount').html(countLog());
}

/**
 * ログ行を作る
 * @param logData ログデータ
 * @returns １行分のデータ
 */
function getLogRow(logData) {

	let row = $('<tr />').append([
	$('<input />').attr({type: 'hidden',	name: 'workdate[]'}			).val(logData.workdate),
	$('<input />').attr({type: 'hidden',	name: 'worktime[]'}			).val(logData.worktime),
	$('<input />').attr({type: 'hidden',	name: 'callsign[]'}			).val(logData.callsign),
	$('<input />').attr({type: 'hidden',	name: 'frequency[]'}		).val(logData.frequency),
	$('<input />').attr({type: 'hidden',	name: 'mode[]'}				).val(logData.mode),
	$('<input />').attr({type: 'hidden',	name: 'modecat[]'}			).val(logData.modecat),
	$('<input />').attr({type: 'hidden',	name: 'recv_rst[]'}			).val(logData.recv_rst),
	$('<input />').attr({type: 'hidden',	name: 'recv_multi[]'}		).val(logData.recv_multi),
	$('<input />').attr({type: 'hidden',	name: 'sent_rst[]'}			).val(logData.sent_rst),
	$('<input />').attr({type: 'hidden',	name: 'sent_multi[]'}		).val(logData.sent_multi),
	$('<input />').attr({type: 'hidden',	name: 'worked_callsign[]'}	).val(''),
	$('<td />').addClass('fs-6 ps-2 align-middle datetime').append(
		$('<span />').addClass('workdate').html(logData.workdate),
		$('<span />').addClass('worktime').html(logData.worktime)),
	$('<td />').addClass('fs-6 ps-2 align-middle callsign').html(logData.callsign),
	$('<td />').addClass('fs-6 ps-2 align-middle frequency').html(bands[logData.frequency] + ' MHz'),
	$('<td />').addClass('fs-6 ps-2 align-middle mode').html(logData.mode),
	$('<td />').addClass('fs-6 ps-2 align-middle sentNumber').append([
		$('<span />').addClass('sent_rst').html(logData.sent_rst),
		$('<span />').addClass('sent_multi').html(logData.sent_multi)]),
	$('<td />').addClass('fs-6 ps-2 align-middle recvNumber').append([
		$('<span />').addClass('recv_rst').html(logData.recv_rst),
		$('<span />').addClass('recv_multi').html(logData.recv_multi)])]);

	return row;
}

/**
 * ログ件数を数える
 */
function countLog() {

	return $('table#log > tbody > tr').length - $('table#log > tbody > tr#input').length - $('table#log > tbody > tr#message').length;
}

/**
 * ログデータを取り込む
 * @param formData フォームデータ
 */
function importLog(formData) {

	$.ajax({
		type:			METHOD_TYPE,
		url:			URL_AJAX,
		dataType:		'json',
        cache:			false,
        contentType:	false,
        processData:	false,
		data:			formData,
		beforeSend:		function (jqXHR) {
			$('div#wait').show();
		}
	}).done(function (data, textStatus, jqXHR) {
		if (data.success) {
			$('input#timezone').val(data.summary.timezone);
			$('input#file_name').val(data.summary.file_name);

			$('select#category').val(data.summary.category).change();
			$('input#owner').val(data.summary.owner);
			$('input#name').val(data.summary.name);
			$('input#address').val(data.summary.address);
			$('input#email').val(data.summary.email);
			$('input#comments').val(data.summary.comments);
			$('input#multioplist').val(data.summary.multioplist);
			$('input#regclubnumber').val(data.summary.regclubnumber).blur();
//			$('td#logType').html(data.logType);

			if (data.summary.timezone == '+09') {
				$('span#timezone').html('JST');

			} else if (data.summary.timezone == '+00') {
				$('span#timezone').html('UTC');
			}

			if (data.RESULTCD == 1) {
				// ログデータが解析できなかったら
				$('table#log').hide();

			} else {
				// ログデータが解析できたら
				$('table#log > tbody > tr[id!=input]').remove();

				// 暫定スコアを記入
				$('table#score > tbody > tr > td').empty();
				for (let frequency in data.summary.scores) {
					$('table#score td#numqso_' + frequency).html(data.summary.scores[frequency].num_qso);
					$('table#score td#point_'  + frequency).html(data.summary.scores[frequency].point);
					$('table#score td#multi_'  + frequency).html(data.summary.scores[frequency].multi);
					$('table#score td#score_'  + frequency).html(data.summary.scores[frequency].score);
				}

				$('td#logCount').html(data.summary.log_data.length);
				for (let i = 0; i < data.summary.log_data.length; i++) {
					// １件のログデータを作る
					let newLine = getLogRow(data.summary.log_data[i]);
					// 空白を付ける
					$(newLine).append($('<td />').addClass('button').html('&nbsp;'));

					$('table#log > tbody').append(newLine);
				}

				$('tr#input').hide();
				$('tr#message').hide();
				$('table#log').show();
			}

			showAlertDialog(contest.contest_name, '<ol><li>内容が正しいか確認して、画面最下部の「提出」ボタンを押してください</li><li>間違っている場合は修正または再度取り込みを行ってください</li><li>画面の内容をクリアするには、このページを再読み込みしてください</li></ol>');

		} else {
			showAlertDialog(contest.contest_name, '[' + data.code + ']' + data.message);
		}

		$('div#wait').hide();

	}).fail(function (jqXHR, textStatus, errorThrown) {

	}).always(function () {

	});
}

/**
 * ログを提出する
 * @param formData フォームデータ
 */
function registerLog(formData) {

	formData.contest_id = contest_id;

	$.ajax({
		type:			METHOD_TYPE,
		url:			URL_AJAX,
		dataType:		'html',
        cache:			false,
        contentType:	false,
        processData:	false,
		data:			formData,
		beforeSend:		function (jqXHR) {
			$('div#wait').show();
		}
	}).done(function (data, textStatus, jqXHR) {
		let result = JSON.parse(data);
		if (result.success) {
			showAlertDialog(contest.contest_name, 'ログの提出が完了しました', [
				$('<button />').addClass('btn btn-sm btn-primary').attr({onclick: '$("div#dialog").modal("hide");location.href="listLog.html?' + contest_id + '";'}).html('ＯＫ')]);
		}
		$('div#wait').hide();

	}).fail(function (jqXHR, textStatus, errorThrown) {

	}).always(function () {

	});
}
