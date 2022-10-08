from wtforms import fields, form
from flask_ckeditor import CKEditorField


class BrandTemplateForm(form.Form):
    image = CKEditorField(render_kw={
        
    })
    text = fields.StringField(
        '특성',
        render_kw={"style": "width:80%;"}
    )


class DescriptionTemplateForm(form.Form):
    image = CKEditorField(render_kw={
        
    })
    title = fields.StringField(
        '특성제목',
        render_kw={"style": "width:80%;"}
    )

    text = fields.StringField(
        '특성내용',
        render_kw={"style": "width:80%;"}
    )
