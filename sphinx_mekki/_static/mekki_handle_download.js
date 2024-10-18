function b64_to_blob(b64d, mt) {
 mt = mt || '';
 ss = 1024;
 var bc = atob(b64d);
 var bas = [];
 for (var ofs = 0; ofs < bc.length; ofs += ss) {
  var slice = bc.slice(ofs, ofs + ss);
  var bnum = new Array(slice.length);
  for (var i = 0; i < slice.length; i++) {
   bnum[i] = slice.charCodeAt(i);
  }
  var ba = new Uint8Array(bnum);
  bas.push(ba);
 }
 var blob = new Blob(bas, {type: mt});
 return blob;
}

function mekki_handle_download(content, mt, id) {
 var blob = b64_to_blob(content, mt);
 document.getElementById(id).href = window.URL.createObjectURL(blob);
}
