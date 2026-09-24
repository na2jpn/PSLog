/**
 * 共通Javascriptファイル
 * @author JJ4KME
 */
let queryParams = parseQuery();

/**
 * アラートダイアログを表示する
 * @param title タイトル
 * @param message メッセージ
 * @param buttons ボタン定義
 */
function showAlertDialog(title, message, buttons) {

	if (buttons === undefined) {
		buttons = [
			$('<button />').addClass('btn btn-primary').attr({onclick: "$('div#dialog').modal('hide');"}).html('ＯＫ')];
	}
	$('div#dialog span.modal-title').html(title);
	$('div#dialog div.modal-body').html(message);
	$('div#dialog div.modal-footer').empty();
	$('div#dialog div.modal-footer').append(buttons);

	$('div#dialog').modal('show');
}

/**
 * ログイン中か調べる
 * @returns ログイン中だったらtrue、ログインしていなかったらfalse
 */
function checkLoggedIn() {

	let cookies = Cookie.get();
	if (cookies === null) {
		return false;

	} else if (!cookies.hasOwnProperty('access_token')) {
		return false;
	}

	return true;
}

/**
 * クエリー文字列を分解する
 * @returns パースされたクエリー文字列
 */
function parseQuery() {

	let result = {};
	if (location.search != '') {
		let source = location.search.substr(1);
		let temp = [];
		if (source.indexOf('&') == -1) {
			temp[0] = source;

		} else {
			temp = source.split('&');
		}

		for (let i = 0; i < temp.length; i++) {
			if (temp[i].indexOf('=') == -1) {
				result[temp[i]] = null;

			} else {
				temp2 = temp[i].split('=');
				result[temp2[0]] = temp2[1];
			}
		}
	}

	return result;
}

/**
 * クッキーの取得・設定・クリア
 */
class Cookie {
	/**
	 * クッキーを取得
	 * @returns 名称と値のオブジェクト、クッキーが無い時はnull
	 */
	static get() {
		if (document.cookie == '') {
			return null;
		
		} else {
			let result = {};
			let source = document.cookie.split(';');
			for (let i = 0; i < source.length; i++) {
				let temp = source[i].split('=');
				result[temp[0].trim()] = temp[1];
			}
			return result;
		}
	}

	/**
	 * クッキーを設定
	 * @param data データ
	 */
	static set(data) {
		for (let key in data) {
			document.cookie = encodeURIComponent(key) + '=' + encodeURIComponent(data[key]);
		}
	}

	/**
	 * クッキーをクリア
	 */
	static clear() {
		let source = document.cookie.split(';');
		for (let i= 0; i < source.length; i++) {
			document.cookie = `${source[i]}; max-age=0`;
		}
	}
}
