from django.db import models
from apps.oaauth.models import OAUser, OADepartment


# Create your models here.

class Inform(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    # public = models.BooleanField(default=False)
    author = models.ForeignKey(OAUser, on_delete=models.CASCADE, related_name='informs', related_query_name='inform')

    class Meta:
        ordering = ('-create_time',)


class InformRead(models.Model):
    inform = models.ForeignKey(Inform, on_delete=models.CASCADE, related_name='reads', related_query_name='reads')
    user = models.ForeignKey(OAUser, on_delete=models.CASCADE, related_name='reads', related_query_name='reads')
    read_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('inform', 'user')
