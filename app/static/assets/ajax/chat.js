var chatList = $(".chat-list"), chatNotifyList = $('#chatNotifyList');

var timer = {
    period: 10000
};

var synchronization = false;

/**
 *
 * @param force
 */
function scrollToEnd(force) {
    if (chatList[0] !== undefined && chatList.data('maxScroll') !== chatList.scrollTop()) {
        if (chatList.data('maxScroll') === undefined) {
            chatList.data({
                maxScroll: chatList.scrollTop(chatList[0].scrollHeight).scrollTop()
            });
        } else if (chatList.data('maxScroll') - chatList.height() / 5 < chatList.scrollTop() || force) {
            $('#scrollStatus').addClass('text-primary');
            chatList.animate({
                scrollTop: chatList[0].scrollHeight
            }, 500, function () {
                $('#scrollStatus').removeClass('text-primary');
            });
        }
    }
}

function fillChatList(messages) {
    var lastMessageId = chatList.children(':last').data('msg_id');

    if (messages.length > 0 && messages[messages.length - 1].message.id !== lastMessageId && messages.length > 0) {
        // Clear message list's
        chatNotifyList.children().remove();
        chatList.children().remove();

        // Retrieve messages
        var messageList = [], notifyMessageList = [];

        for (var i in messages) {
            var msg = messages[i];

            var li = makeMessageItem(msg).data({msg_id: msg.message.id});

            messageList.push(li);

            if (i >= messages.length - 5) {
                notifyMessageList.push(li.clone());
            }
        }

        if (chatList[0] !== undefined) {
            chatList.append(messageList);
        }

        if (chatNotifyList[0] !== undefined) {
            chatNotifyList.append(notifyMessageList);
        }
    }

    scrollToEnd();
}

/**
 *
 * @param lastMsg
 */
function requestMessages() {
    synchronization = true;

    var reqData = { count: 25 };

    if (chatList.attr('group') != undefined) {
        reqData.group = chatList.attr('group');
    }

    // From "server.js"
    sendAction('/messages/read', reqData, function (data) {
        synchronization = false;

        setStatus('synced');

        fillChatList(data[0].chat);
    }, function (e) {
        synchronization = false;

        setStatus('error');
    });
}

/**
 *
 * @param msg
 * @returns {*|jQuery}
 */
function makeMessageItem(msg) {
    var img = $('<img class="img-circle" style="width: 35px;" />');
    img.attr('src', msg.account.picture);
    img.attr('alt', msg.account.name);

    return $('<li/>').append($('<figure class="image rounded"/>').append(img))
        .append($('<span class="title"/>').append($('<span class="pull-right text-xs text-muted"/>').html(msg.message.time)).append(msg.account.name))
        .append($('<span class="message truncate"/>').append(msg.message.text.replace('\n', '<br/>')));
}

/**
 *
 * @param status
 */
function setStatus(status) {
    if (status.indexOf('sync') >= 0) {
        $('#chatStatus').removeClass('fa-times text-secondary').addClass('fa-spin text-primary');
    }

    if (status.indexOf('synced') >= 0) {
        $('#chatStatus').removeClass('fa-spin text-primary').addClass('fa-refresh');
    }

    if (status.indexOf('error') >= 0) {
        $('#chatStatus').removeClass('fa-spin text-primary fa-refresh').addClass('fa-times text-secondary');
    }
}

/**
 *
 * @param chatForm
 */
function sendMessage(chatForm) {
    try {
        // Disable input
        chatForm.attr('disabled', 'disabled');

        sendAction('/messages/send', chatForm.serializeObject(), function () {
            requestMessages();

            chatForm.removeAttr('disabled')[0].reset();
        }, function (e) {
            chatForm.removeAttr('disabled');
        });
    } catch (e) {
        console.log(e);
    }
}

/**
 *
 * @param nowait
 */
function forceUpdate(nowait) {
    if (!synchronization) {
        synchronization = true;
        setStatus('sync');

        if (nowait) {
            backgroundSync(false);

            requestMessages();

            backgroundSync(true);
        } else {
            backgroundSync(false);

            setTimeout(function () {
                requestMessages();
                backgroundSync(true);
            }, 2000);
        }
    }
}

function backgroundSync(turn) {
    clearTimeout(timer.id);

    if (turn) {
        timer.id = setTimeout(forceUpdate, timer.period);
    }
}

if (chatList[0] !== undefined || chatNotifyList[0] !== undefined) {
    forceUpdate(true);
}