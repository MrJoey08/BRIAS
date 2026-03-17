/* BRIAS — Shared Config */

var BRIAS_API = 'https://api.brias.eu';

function briasApi(path, opts) {
  opts = opts || {};
  var token = localStorage.getItem('brias_token');
  var headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  if (opts.headers) { for (var k in opts.headers) headers[k] = opts.headers[k]; }
  opts.headers = headers;
  return fetch(BRIAS_API + path, opts);
}

function briasCheckOnline() {
  return fetch(BRIAS_API + '/api/me', { method: 'GET', signal: AbortSignal.timeout(3500) })
    .then(function() { return true; })
    .catch(function() { return false; });
}
