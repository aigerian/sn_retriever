function printJSON(json) {
    	$('#json').val(JSON.stringify(json));
	}

function sendResultFeedback(result_id, feedback){
		$.ajax({
			url:'/process_search/'+result_id,
			method: 'POST',
			data:feedback
		});
}

$( document ).ready(function(){
	var loading_text = $('#loading_text');
	loading_text.hide();

	var result_menu = $('#result_menu');
	result_menu.hide();

	$('#result_menu>#good').bind('click', function(){
		var id = result_menu.attr('target_root_id');
		sendResultFeedback(id,true);
	});

	$('#result_menu>#bad').bind('click', function(){
		var id = result_menu.attr('target_root_id');
		sendResultFeedback(id,false);
	});

	$('#search_form').submit(function(event){
		event.preventDefault();
		var formData = $(this).serializeArray();
		var formURL = $(this).attr("action");
		loading_text.fadeIn(100);
		result_menu.fadeOut(100);

		$.ajax({
			url:formURL,
			method:'POST',
			data:formData,
			success:function(data){
				var opt = {
					change:function(data){
						$('#path').text(path);
					},
					propertyclick:function(data){
						json = data;
    					printJSON(json);
					},
					propertyElement:'<input>',
					valueElement:'<input>'
				};
				if (data['success'] == 'true'){
					$('#search_result').jsonEditor(data['result'], opt);
					result_menu.attr('target_root_id',data['target_root'])
				}
			},
			complete:function(){
				loading_text.fadeOut(100);		
				result_menu.fadeIn(100);
			}
		})
		return false;
	});
});