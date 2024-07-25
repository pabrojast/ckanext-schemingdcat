$(document).ready(function() {
    // Initialize the first tab and pane as active
    $("#groupTab .nav-pills li:first").addClass("active");
    $("#groupTab .tab-pane:first").addClass("active fade in");

    // Move forward
    $("#next-tab").on('click', function(e) {
        $('.dataset-form .nav > .active').next('li').find('a').trigger('click');
        // Check if there is another tab, if not, swap buttons
        if ($('.dataset-form .nav > .active').next('li').length == 0) {
            $('#next-tab').hide();
        }
        e.preventDefault();
        return false;
    });

    // Hide initially
    //$('#next-tab+button').hide();

    // Remove duplicate form groups
    var seenFormGroups = new Set();
    $("#groupTab .tab-pane .card").each(function() {
        var formGroupId = $(this).attr("class").split('-group')[0];
        if (seenFormGroups.has(formGroupId)) {
            $(this).remove();
        } else {
            seenFormGroups.add(formGroupId);
        }
    });

    // Note: Uncomment the #next-tab+button selectors to hide the submit button till you've
    // hit the last tab of schema items.
});