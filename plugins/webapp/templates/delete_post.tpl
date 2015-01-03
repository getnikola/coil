<%inherit file="base.tpl" />
<%block name="head">
</%block>
<%block name="content">
<h1 class="title">Really delete "${post.title()}"?</h1>
<a class="btn btn-danger" href="/really_delete/${path}">Yes, really.</a>
<a class="btn btn-default" href="/">No</a>
</%block>
