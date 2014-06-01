function get_sn_swithcers(){
    //returning sithcers on which social net i must search
}


function generateUUID() {
    var d = new Date().getTime();
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = (d + Math.random() * 16) % 16 | 0;
        d = Math.floor(d / 16);
        return (c == 'x' ? r : (r & 0x7 | 0x8)).toString(16);
    });
    return uuid;
}


    function sendResultFeedback(result_id, feedback) {
    $.ajax({
        url: '/process_search/' + result_id,
        method: 'POST',
        data: feedback
    });
}
function getSearchResult(search_id, container, state) {
    var stopId = setInterval(function () {
        $.ajax({
            url: '/search_result/' + search_id,
            method: 'POST',
            success: function (data) {
                console.log('receiving search data');
                console.log(data);
                if (data['success'] == 'true') {
                    if (data['ended'] == 'true') {
                        clearInterval(stopId);
                        state.text('Completed!');
                        container.jsonEditor(data['result']);
                    }
                } else {
                    clearInterval(stopId);
                }
            }
        });

    }, 3000);
}
function initSearchResult(search_id, search_q, formData) {
    var srContainer = $('#sr_container');

    rc = $('<div/>', {class: 'panel panel-default'});
    rc.appendTo(srContainer);


    rt = $('<div/>', {class: 'panel-heading'});
    rt.appendTo(rc);

    rtc = $('<a/>', {'data-toggle': 'collapse', 'data-parent': 'sr_container', href: '#' + search_id});
    rtc.appendTo(rt);

    rt_name = $('<div/>', {class: 'result_name'});
    rt_state = $('<div/>', {class: 'result_state'});
    rt_name.text('Search for: ' + search_q);
    rt_state.text('Please wait...');
    rt_state.appendTo(rtc);
    rt_name.appendTo(rtc);

    rb = $('<div/>', {class: 'panel-collapse collapse', id: search_id});
    rb.appendTo(rc);

    rbc = $('<div/>', {class: 'panel-body json-editor'});
    rbc.appendTo(rb);
    console.log(formData);
    formData.push({name: 'search_id', value: search_id});
    $.ajax({
        url: '/search',
        method: 'POST',
        data: formData,
        success: function (data) {
            console.log('receiving search');
            console.log(data);
            if (data['success'] == 'true') {
                getSearchResult(search_id, rbc, rt_state);
            }
        }
    });
}

$(document).ready(function () {

    $('#search_form').submit(function (event) {
        event.preventDefault();
        var formData = $(this).serializeArray();
        var search_q = $(this).find('#form_input').val();
        var search_id = generateUUID();
        initSearchResult(search_id, search_q, formData);
    });
});