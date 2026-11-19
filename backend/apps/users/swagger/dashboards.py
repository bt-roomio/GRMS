from main.serializers.dashboard import MyDashboardSerializer, SimpleDashboardSerializer

MyDashboardsSwagger = {200: SimpleDashboardSerializer(many=True)}

MyDashboardDetailSwagger = {200: MyDashboardSerializer}
