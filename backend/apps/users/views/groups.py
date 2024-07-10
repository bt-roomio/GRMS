from django.contrib.auth.models import Group
from rest_framework.views import APIView, Response
from users.serializers.group import GroupSerializer


class GroupsListView(APIView):
    def get(self, request):
        instance = Group.objects.all()
        serializer = GroupSerializer(instance, many=True)
        return Response(serializer.data)
