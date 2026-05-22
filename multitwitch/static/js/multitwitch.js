var chat_hidden = false;
var num_streams = -1;
var streams = new Array();
var chat_tabs;
var followedChannelsLoaded = false;
var followedChannelsLoading = false;
var followedChannelsData = new Array();

function twitch_parent_query() {
    var parts = new Array();
    for (var i = 0; i < twitchParents.length; i++) {
        parts.push('parent=' + encodeURIComponent(twitchParents[i]));
    }
    return parts.join('&');
}

function optimize_size(n) {
    // Call with n = -1 to use previously known quantity
    if (n == -1) {
        if (num_streams == -1) {
            return;
        } else {
            n = num_streams;
        }
    } else {
        if (n == 0) {
            $("#helpbox").show();
            hide_chat();
        } else {
            $("#helpbox").hide();
            if (num_streams == 0) {
                show_chat();
                chat_tabs.tabs({ active: 0 });
            }
        }
        num_streams = n;
    }

    // Resize chat
    // height is off by 16 due to body margin
    var height = $(window).innerHeight() - 16;
    var width = $("#streams").width();
    if(!chat_hidden) {
        var chat_width = 304;
        var wrapper_width = $("#wrapper").width();
        width = wrapper_width - chat_width - 5;
        var chat_height = height - $("#tablist").height() - 24;
        $("#streams").width(width);
        $("#chatbox").width(chat_width);
        $(".stream_chat").height(chat_height);
    } else {
        var wrapper_width = $("#wrapper").width();
        width = wrapper_width;
        $("#streams").width(width);
    }

    var best_height = 0;
    var best_width = 0;
    var wrapper_padding = 0;
    for (var per_row = 1; per_row <= n; per_row++) {
        var num_rows = Math.ceil(n / per_row);
        var max_width = Math.floor(width / per_row) - 4;
        var max_height = Math.floor(height / num_rows) - 4;
        if (max_width * 9/16 < max_height) {
            max_height = max_width * 9/16;
        } else {
            max_width = (max_height) * 16/9;
        }
        if (max_width > best_width) {
            best_width = max_width;
            best_height = max_height;
            wrapper_padding = (height - num_rows * max_height)/2;
        }
    }
    $(".stream_tile").height(Math.floor(best_height));
    $(".stream_tile").width(Math.floor(best_width));
    $(".stream").height('100%');
    $(".stream").width('100%');
    $("#streams").css("padding-top", wrapper_padding);
}

function absolute_center(object) {
    var window_height = $(window).height();
    var window_width = $(window).innerWidth();
    var obj_height = object.height();
    var obj_width = object.width();
    var pos_x = (window_width - obj_width)/2;
    var pos_y = (window_height - obj_height)/2;
    if (pos_x < 0) {
        pos_x = 0;
    }
    if (pos_y < 0) {
        pos_y = 0;
    }
    object.css('position', 'absolute');
    object.css('left', pos_x);
    object.css('top', pos_y);
}

function hide_chat() {
    chat_hidden = true;
    $("#chatbox").hide();
    optimize_size(-1);
}

function show_chat() {
    chat_hidden = false;
    $("#chatbox").show();
    optimize_size(-1);
}

function toggle_chat() {
    if (chat_hidden) {
        show_chat();
    } else {
        hide_chat();
    }
}

function change_streams() {
    position_change_streams();
    $("#change_streams").show();
    load_followed_channels_once();
    focus_last_stream_box();
}

function add_stream_item() {
    $("#streamlist").append($(item_string));
    position_change_streams();
    focus_last_stream_box();
}

function stream_item_keyup(e) {
    if (e.keyCode == 13 || e.which == 13) {
        add_stream_item();
        return false;
    }
    return true;
}

function stream_object(name) {
    return $('<div class="stream_tile" data-stream-name="' + name + '"><button type="button" class="stream_close" onclick="close_stream_by_button(this)" title="Close stream">x</button><iframe id="embed_' + name + '" src="https://player.twitch.tv/?muted=true&channel=' + name + '&' + twitch_parent_query() + '" class="stream" allowfullscreen="true"></iframe></div>');
}

function chat_object(name) {
    return $('<div id="chat-' + name + '" class="stream_chat"><iframe frameborder="0" scrolling="no" id="chat-' + name + '-embed" src="https://twitch.tv/embed/' + name + '/chat?' + twitch_parent_query() + '" height="100%" width="100%"></iframe></div>');
}

function chat_tab_object(name) {
    return $('<li><a href="#chat-' + name + '">' + name + '</a></li>');
}

var item_string = '<div class="streamlist_item"><input type="text" class="stream_name" onkeyup="stream_item_keyup(event)" /></div>';

function update_stream_list() {
    // Update the contents of #streamlist to match streams
    $("#streamlist .streamlist_item").remove();
    for (var i = 0; i < streams.length; i++) {
        $("#streamlist").append($('<div class="streamlist_item"><input type="checkbox" class="check" checked=true" /> <span>' + streams[i] + '</span></div>'));
    }
    $("#streamlist").append($(item_string));
}

function focus_last_stream_box() {
    stream_boxes = $("#streamlist .stream_name");
    if (stream_boxes.length > 0) {
        stream_boxes[stream_boxes.length - 1].focus();
    }
}

function position_change_streams() {
    var modal = $("#change_streams");
    var modalWidth = modal.outerWidth();
    modal.css('position', 'fixed');
    modal.css('top', '15vh');
    modal.css('left', '50%');
    modal.css('margin-left', -(modalWidth / 2) + 'px');
}

function update_url() {
    var new_url = "";
    for (var i = 0; i < streams.length; i++) {
        new_url = new_url + '/' + streams[i];
    }
    if (new_url == "") {
        new_url = "/";
    }
    history.replaceState(null, "", new_url);
}

function sync_chat_visibility() {
    if (streams.length === 0) {
        hide_chat();
        $("#helpbox").show();
        return;
    }
    $("#helpbox").hide();
    if (chat_hidden) {
        show_chat();
    }
}

function add_stream(stream_name) {
    for (var i = 0; i < streams.length; i++) {
        if (streams[i] == stream_name) {
            return;
        }
    }
    streams.push(stream_name);
    $("#streams").append(stream_object(stream_name));
    $("#chatbox").append(chat_object(stream_name));
    $("#tablist").append(chat_tab_object(stream_name));
    chat_tabs.tabs("refresh");
    sync_chat_visibility();
    optimize_size(streams.length);
    update_stream_list();
    update_url();
}

function close_stream_by_button(button) {
    var tile = $(button).closest(".stream_tile");
    var tiles = $("#streams .stream_tile");
    var index = tiles.index(tile);
    if (index === -1) {
        return false;
    }
    remove_stream_at_index(index);
    return false;
}

function remove_stream_at_index(index) {
    if (index < 0 || index >= streams.length) {
        return;
    }
    var stream_name = streams[index];
    streams.splice(index, 1);
    $("#streams .stream_tile").eq(index).remove();

    if ($.inArray(stream_name, streams) === -1) {
        $("#chat-" + stream_name).remove();
        $('#tablist a[href="#chat-' + stream_name + '"]').parent().remove();
        chat_tabs.tabs("refresh");
    }

    sync_chat_visibility();
    optimize_size(streams.length);
    update_stream_list();
    update_url();
}

function close_change_streams(apply) {
    var new_streams;
    if(apply) {
        // Remove all the streams that got unchecked
        new_streams = new Array();
        var stream_elements = $("#streams .stream_tile");
        var chat_elements = $("#chatbox .stream_chat");
        var chat_tab_elements = $("#tablist li");
        var list_checks = $("#streamlist .check");
        for (var i = 0; i < streams.length; i++) {
            if (!list_checks[i].checked) {
                stream_elements[i].remove();
                chat_elements[i].remove();
                chat_tab_elements[i].remove();
            } else {
                new_streams.push(streams[i]);
            }
        }
        // add new streams
        var new_stream_inputs = $("#streamlist .stream_name");
        for (var i = 0; i < new_stream_inputs.length; i++) {
            var stream_name = new_stream_inputs[i].value;
            if (stream_name == "") {
                continue;
            }
            if ($.inArray(stream_name, new_streams) != -1) {
                continue;
            }
            new_streams.push(stream_name);
            $("#streams").append(stream_object(stream_name));
            $("#chatbox").append(chat_object(stream_name));
            $("#tablist").append(chat_tab_object(stream_name));
            chat_tabs.tabs("refresh");
        }
        streams = new_streams;
        sync_chat_visibility();
        optimize_size(streams.length);
        update_url();
    }
    $("#change_streams").hide();
    update_stream_list();
}

function load_followed_channels_once() {
    if (!followedChannelsLoaded && !followedChannelsLoading) {
        load_followed_channels();
    }
}

function load_followed_channels() {
    followedChannelsLoading = true;
    $("#followed_channels_status").text("Loading followed channels...");
    $("#followed_channels_list").empty();
    clear_followed_channels_filter();
    $.getJSON('/api/followed-channels', function(data) {
        followedChannelsLoaded = true;
        followedChannelsLoading = false;
        if (!data.configured) {
            $("#followed_channels_status").text("Twitch integration is not configured on the server.");
            return;
        }
        if (!data.connected) {
            $("#followed_channels_status").text("Connect your Twitch account to load the channels you follow.");
            return;
        }
        if (data.error) {
            $("#followed_channels_status").text(data.error);
            return;
        }
        $("#followed_channels_status").text("Click a channel to add it to the layout.");
        followedChannelsData = data.channels || [];
        render_followed_channels(followedChannelsData);
    }).fail(function(xhr) {
        followedChannelsLoading = false;
        $("#followed_channels_status").text(parse_failed_followed_channels_response(xhr));
    });
}

function render_followed_channels(channels) {
    $("#followed_channels_list").empty();
    if (!channels || channels.length === 0) {
        $("#followed_channels_list").append($('<div class="followed_channel empty">No followed channels found.</div>'));
        return;
    }
    for (var i = 0; i < channels.length; i++) {
        $("#followed_channels_list").append(followed_channel_object(channels[i]));
    }
}

function clear_followed_channels_filter() {
    var filterInput = $("#followed_channels_filter");
    if (filterInput.length > 0) {
        filterInput.val('');
    }
}

function filter_followed_channels() {
    var filterInput = $("#followed_channels_filter");
    if (filterInput.length === 0) {
        return;
    }
    var query = $.trim(filterInput.val().toLowerCase());
    if (query === "") {
        render_followed_channels(followedChannelsData);
        return;
    }
    var filtered = new Array();
    for (var i = 0; i < followedChannelsData.length; i++) {
        var channel = followedChannelsData[i];
        var haystack = [
            channel.name || '',
            channel.login || '',
            channel.game_name || '',
            channel.title || ''
        ].join(' ').toLowerCase();
        if (haystack.indexOf(query) !== -1) {
            filtered.push(channel);
        }
    }
    render_followed_channels(filtered);
}

function parse_failed_followed_channels_response(xhr) {
    if (xhr && xhr.responseJSON && xhr.responseJSON.error) {
        return xhr.responseJSON.error;
    }
    if (xhr && xhr.responseText) {
        try {
            var data = JSON.parse(xhr.responseText);
            if (data.error) {
                return data.error;
            }
        } catch (error) {
        }
        return xhr.responseText;
    }
    return "Could not load followed channels.";
}

function followed_channel_object(channel) {
    var row = $('<button type="button" class="followed_channel"></button>');
    var nameRow = $('<div class="followed_channel_name_row"></div>');
    var name = $('<span class="followed_channel_link"></span>');
    var status = $('<span class="followed_channel_badge"></span>');

    name.text(channel.name);
    status.text(channel.is_live ? 'LIVE' : 'OFFLINE');
    if (channel.is_live) {
        status.addClass('live');
    } else {
        status.addClass('offline');
    }

    row.attr('data-login', channel.login);
    row.click(function() {
        add_stream(channel.login);
        update_stream_list();
        return false;
    });
    nameRow.append(name);
    nameRow.append(status);
    row.append(nameRow);
    if (channel.game_name || channel.title) {
        var metaText = '';
        if (channel.game_name) {
            metaText += channel.game_name;
        }
        if (channel.title) {
            if (metaText !== '') {
                metaText += ' - ';
            }
            metaText += channel.title;
        }
        row.append($('<div class="followed_channel_meta"></div>').text(metaText));
    }
    return row;
}
