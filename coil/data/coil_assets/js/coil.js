/*
 * Copyright © 2014-2017 Chris Warrick, Roberto Alsina, Henry Hirsch et al.
 * See /LICENSE for licensing information.
 */

function save_anim() {
    $(".save-btn").removeClass("btn-primary").addClass("btn-success");
    $(".save-icon").removeClass("fa-save").addClass("fa-check");
    setTimeout(function() {
        $(".save-btn").removeClass("btn-success").addClass("btn-primary");
        $(".save-icon").removeClass("fa-check").addClass("fa-save");
    }, 2000);
}

function save_fail_anim() {
    $(".save-btn").removeClass("btn-primary").addClass("btn-danger");
    $(".save-icon").removeClass("fa-save").addClass("fa-times");
    setTimeout(function() {
        $(".save-btn").removeClass("btn-danger").addClass("btn-primary");
        $(".save-icon").removeClass("fa-times").addClass("fa-save");
    }, 2000);
}
