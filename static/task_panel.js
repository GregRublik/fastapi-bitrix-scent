const button = document.querySelector('#button-accountant');
button.addEventListener('click', function() {
    BX24.init(function(){
        BX24.callMethod('user.current', {}, function(res){
            alert('Привет ' + res.data().ID + '!');
        });
    });
});