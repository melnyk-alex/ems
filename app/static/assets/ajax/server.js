/**
 * Serialization <form />.
 * @returns {} <form /> object.
 */
$.fn.serializeObject = function () {
    var sObject = {};
    $(this.serializeArray()).each(function () {
        if (sObject[this.name] !== undefined) {
            if (!sObject[this.name].push) {
                sObject[this.name] = [sObject[this.name]];
            }
            sObject[this.name].push(this.value || '');
        } else {
            sObject[this.name] = this.value || '';
        }
    });
    return sObject;
};


function doAction(url, what, value) {
    var form = $(value);
    var data = form.serializeObject();
    data.ref = document.location.pathname;
    //console.log(data);

    sendAction(url + "/" + what, data, function (data) {
        form.nextAll().remove();

        for (var k in data) {
            var resp = data[k];

            if (resp.status !== undefined) {
                switch (resp.status) {
                    case "success":
                        $.magnificPopup.close();
                        notify(resp);
                        break;
                    case "error":
                    default:
                        form.after($('<div />').addClass('alert alert-' + resp.status)
                            .append($('<strong />').html(resp.title)).append(" " + resp.text));
                        break;
                }
            }

            if (resp.exec !== undefined) {
                //console.log(resp.exec);
                if (resp.exec instanceof Object) {
                    setTimeout('eval("' + resp.exec.script + '")', resp.exec.timeout | 500);
                } else {
                    setTimeout('eval("' + resp.exec + '")', 500);
                }
            }
        }
    });

    return false;
}

function sendAction(url, data, success, error) {
    try {
        $.ajax(url, {
            method: "post",
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            success: success,
            error: function (e) {
                if (error !== undefined) {
                    error(e);
                }
                console.log(e);
            }
        });
        return true;
    } catch (e) {
        console.log(e);
    }

    return false;
}

/**
 * Notification
 * @param notifyObject
 */
function notify(notifyObject) {
    new PNotify($.extend({
        shadow: true,
        nonblock: {
            nonblock: true,
            nonblock_opacity: .2
        }
    }, notifyObject));
}