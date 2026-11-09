"""Gol: StudentScore.gol (jami) va StudentPointLog → gol tarixi (kundalik kirish + haftalik test)."""
from django.db import migrations, models
from django.db.models import Sum


def move_daily_reward_to_gol(apps, schema_editor):
    """0020 bilan berilgan kundalik mukofot ballga (score) qo'shilgan edi — endi u gol: balldan
    ayirib, golga o'tkaziladi."""
    StudentPointLog = apps.get_model('app_student', 'StudentPointLog')
    StudentScore = apps.get_model('app_student', 'StudentScore')
    totals = (
        StudentPointLog.objects.filter(source='daily_login')
        .values('student_id').annotate(total=Sum('gol'))
    )
    for row in totals:
        score = StudentScore.objects.filter(student_id=row['student_id']).first()
        if score is None:
            continue
        score.score = max(0, score.score - row['total'])
        score.gol += row['total']
        score.save(update_fields=['score', 'gol'])
        running = 0
        for log in StudentPointLog.objects.filter(student_id=row['student_id']).order_by('created_at'):
            running += log.gol
            log.gol_after = running
            log.save(update_fields=['gol_after'])


class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0020_studentpointlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentscore',
            name='gol',
            field=models.PositiveIntegerField(default=0, verbose_name='Gol'),
        ),
        migrations.RemoveConstraint(
            model_name='studentpointlog',
            name='uniq_student_point_source_date',
        ),
        migrations.RenameField(
            model_name='studentpointlog',
            old_name='points',
            new_name='gol',
        ),
        migrations.RenameField(
            model_name='studentpointlog',
            old_name='score_after',
            new_name='gol_after',
        ),
        migrations.AlterField(
            model_name='studentpointlog',
            name='gol',
            field=models.PositiveIntegerField(verbose_name='Gol'),
        ),
        migrations.AlterField(
            model_name='studentpointlog',
            name='gol_after',
            field=models.PositiveIntegerField(default=0, verbose_name='Jami gol (keyin)'),
        ),
        migrations.AlterField(
            model_name='studentpointlog',
            name='source',
            field=models.CharField(
                choices=[('daily_login', 'Kundalik kirish'), ('weekly_test', 'Haftalik test')],
                max_length=30,
                verbose_name='Manba',
            ),
        ),
        migrations.RunPython(move_daily_reward_to_gol, migrations.RunPython.noop),
        migrations.AddField(
            model_name='studentpointlog',
            name='ref',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Manba ID'),
        ),
        migrations.AlterModelOptions(
            name='studentpointlog',
            options={'ordering': ['-created_at'], 'verbose_name': 'Gol tarixi', 'verbose_name_plural': 'Gol tarixi'},
        ),
        migrations.AddConstraint(
            model_name='studentpointlog',
            constraint=models.UniqueConstraint(
                condition=models.Q(('source', 'daily_login')),
                fields=('student', 'source', 'date'),
                name='uniq_gol_daily_login',
            ),
        ),
        migrations.AddConstraint(
            model_name='studentpointlog',
            constraint=models.UniqueConstraint(
                condition=models.Q(('ref', ''), _negated=True),
                fields=('student', 'source', 'ref'),
                name='uniq_gol_source_ref',
            ),
        ),
    ]
