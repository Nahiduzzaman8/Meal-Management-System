from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404

from apps.users.models import User
from apps.users.permissions import HasCapability
from apps.months.serializers import MonthSerializer, MonthMemberSerializer
from apps.months.services import assign_manager, create_month, open_month, close_month
from apps.months.models import Month, MonthMember


class MonthCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'month.create'

    def post(self, request):
        ser = MonthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            month = create_month(ser.validated_data['name'], ser.validated_data['start_date'], ser.validated_data['end_date'], request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MonthSerializer(month).data, status=status.HTTP_201_CREATED)


class MonthOpenView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'month.open'

    def post(self, request, pk):
        try:
            month = open_month(pk, request.user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MonthSerializer(month).data)


class MonthCloseView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'month.close'

    def post(self, request, pk):
        result = close_month(pk, request.user)
        if result.get('code') == 'month_close_blocked':
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class MonthMembersView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'month.view'

    def get(self, request, pk):
        month = Month.objects.get(pk=pk)
        members = MonthMember.objects.filter(month=month)
        ser = MonthMemberSerializer(members, many=True)
        return Response(ser.data)


class ManagerAssignView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'manager.assign'

    def put(self, request, pk):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'code': 'user_id_required', 'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        month = get_object_or_404(Month, pk=pk)
        target_user = get_object_or_404(User, pk=user_id)

        try:
            assignment = assign_manager(month, target_user, request.user)
        except ValueError as exc:
            msg = str(exc)
            code = 'manager_assignment_invalid'
            if 'active manager' in msg.lower():
                code = 'already_active_manager'
            elif 'must be active' in msg.lower():
                code = 'inactive_target_user'
            elif 'Only active MEMBER' in msg:
                code = 'invalid_manager_target'
            return Response({'code': code, 'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'ok', 'manager': {'id': assignment.user_id, 'username': assignment.user.username}}, status=status.HTTP_200_OK)
