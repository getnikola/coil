/*
 * Copyright © 2014-2015 Roberto Alsina, Henry Hirsch, Chris Warrick.
 *
 * Permission is hereby granted, free of charge, to any
 * person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the
 * Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the
 * Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice
 * shall be included in all copies or substantial portions of
 * the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
 * KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
 * WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
 * PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
 * OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 * OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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

