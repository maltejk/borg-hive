/*
 * Remote modal load Function
 */
var modal = document.getElementById('modal')
modal.addEventListener('show.coreui.modal', function(e) {
  console.log(e)
  var url;
  if (e.relatedTarget.href !== undefined ){
    url = e.relatedTarget.href
  } else if ('data-url' in e.relatedTarget.attributes ){
    url = e.relatedTarget.attributes['data-url'].value
  }
  fetch(url, {
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
   .then((response) => response.text())
   .then((html) => {
       var content = document.getElementsByClassName('modal-content')
       content[0].innerHTML = html
   })
   .catch((error) => {
       console.warn(error);
   });
 });
