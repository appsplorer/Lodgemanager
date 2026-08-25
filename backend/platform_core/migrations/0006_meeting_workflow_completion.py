import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('platform_core','0005_communications_completion'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AddField(model_name='meeting',name='occurrence_key',field=models.CharField(blank=True,max_length=180)),
        migrations.AddField(model_name='meeting',name='recurrence_source',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='generated_occurrences',to='platform_core.meeting')),
        migrations.AddConstraint(model_name='meeting',constraint=models.UniqueConstraint(condition=~models.Q(occurrence_key=''),fields=('tenant','occurrence_key'),name='uniq_tenant_meeting_occurrence_key')),
        migrations.CreateModel(name='AgendaItem',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('kind',models.CharField(choices=[('standard','standard'),('custom','custom')],default='custom',max_length=20)),('standard_key',models.SlugField(blank=True,max_length=80)),('title',models.CharField(max_length=240)),('notes',models.TextField(blank=True)),('sort_order',models.PositiveIntegerField(default=0)),('is_hidden',models.BooleanField(default=False)),('meeting',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='agenda_items',to='platform_core.meeting')),('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='agenda_items',to='platform_core.tenant'))],options={'ordering':['sort_order','created_at']}),
        migrations.AddIndex(model_name='agendaitem',index=models.Index(fields=['tenant','meeting','sort_order'],name='lf_agenda_order_idx')),
        migrations.AddField(model_name='minuteversion',name='reviewer_comments',field=models.TextField(blank=True)),
        migrations.AddField(model_name='minuteversion',name='reopen_reason',field=models.TextField(blank=True)),
        migrations.AddField(model_name='minuteversion',name='approved_at',field=models.DateTimeField(blank=True,null=True)),
        migrations.AddField(model_name='minuteversion',name='approved_by',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='minutes_approved',to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='minuteversion',name='locked_by',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='minutes_locked',to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='minuteversion',name='reopened_from',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='reopened_versions',to='platform_core.minuteversion')),
    ]
