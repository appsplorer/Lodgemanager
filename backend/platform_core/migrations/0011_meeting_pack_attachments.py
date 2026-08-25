import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[('platform_core','0010_integrity_controls'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name='MeetingAttachment',
            fields=[
                ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,serialize=False,editable=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('label',models.CharField(blank=True,max_length=180)),
                ('sort_order',models.PositiveIntegerField(default=0)),
                ('include_in_pack',models.BooleanField(default=True)),
                ('created_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='meeting_attachments_created',to=settings.AUTH_USER_MODEL)),
                ('document',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='meeting_pack_links',to='platform_core.document')),
                ('meeting',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='pack_attachments',to='platform_core.meeting')),
                ('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='meeting_attachments',to='platform_core.tenant')),
            ],
            options={'ordering':['sort_order','created_at']},
        ),
        migrations.AddConstraint(model_name='meetingattachment',constraint=models.UniqueConstraint(fields=('meeting','document'),name='uniq_meeting_pack_document')),
        migrations.AddIndex(model_name='meetingattachment',index=models.Index(fields=['tenant','meeting','sort_order'],name='lf_meeting_attach_idx')),
    ]
