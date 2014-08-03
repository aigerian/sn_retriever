function retrieve_search_result(search_identity){
    var identity_next;
    $.when($.ajax({
        url:'/get_search_result/'+search_identity,
        method:'GET',
        success:function(data){
            console.log('retrieved data:');
            console.log(data);
            if (data['success']==true){
                return data;
            }
            else{
                console.log('unhandled path!!!');
            }
        }
    })).done(function (data){
        identity_next = data['identity_next'];
        console.log('when we is done we retrieve: '+data);
    });

}

function put_in_beatiful(text){
        var result_container = $.find('#sr_container')[0];
        result_container.append(text);
}

function get_next_object(search_identity) {
    return $.ajax({
            url: '/check_status/' + search_identity,
            method: 'GET',
            success: function (data) {
                console.log('check status: '+search_identity);
                if (data['success'] == true) {
                    if (data['is_ended'] == true) {
                        console.log('end! start retrieveing and posting object');
                        next_identity = retrieve_search_result(search_identity);
                        return next_identity
                    }
                    else{
                        console.log('not end it must be next...');
                    }
                }
            }  
        }); 
}

function retrieve_search_identity(search_q){
    return $.ajax({
        url:'/search',
        method:'POST',
        data:{'query':search_q},
        success: function(data){        
            search_identity = data['identity'];
            console.log('found identity.... '+search_identity);
            return search_identity
        }
    });                 
}

$(document).ready(function () {
    var next_btn = $('#next_button');
    next_btn.hide();
    $('#search_data_form').submit(function (event) {
        event.preventDefault();
        var formData = $(this).serializeArray();
        console.log('sforming data:'+formData);
        var search_q = $(this).find('#search_form_input').val();
        console.log('will search data:'+search_q);

        retrieve_search_identity(search_q).done(function(search_identity){
            get_next_object(search_identity).done(function(next_object){
                next_btn.show();
                console.log(next_object);
                put_in_beatiful(next_object);
            });
        });     
    });
});
