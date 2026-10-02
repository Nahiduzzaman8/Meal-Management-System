from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.contrib.auth import get_user_model
from django.db import models

from apps.users.serializers import UserProfileSerializer, TokenObtainPairSerializer, PasswordChangeSerializer
from apps.users.permissions import ROLE_CAPABILITIES, MANAGER_CAPABILITIES
from apps.users.serializers import UserListSerializer, UserCreateSerializer, UserDetailSerializer
from apps.users.permissions import HasCapability
from apps.users.utils import generate_temp_password
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateAPIView, ListCreateAPIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone

User = get_user_model()


class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.validated_data['user']
        refresh = RefreshToken.for_user(user)
        profile = UserProfileSerializer(user).data
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': profile})


class RefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)


class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'detail': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            return Response({'detail': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        user = request.user
        profile = UserProfileSerializer(user).data
        # compute capabilities
        caps = set(ROLE_CAPABILITIES.get(user.role, set()))
        # admin has manager caps implicitly
        if user.role == 'ADMIN' or user.is_superuser:
            caps.update(MANAGER_CAPABILITIES)
        else:
            # check active manager
            try:
                from apps.months.models import Month, ManagerAssignment
                open_month = Month.objects.filter(status=Month.Status.OPEN).first()
                if open_month:
                    current = ManagerAssignment.current_manager(open_month)
                    if current and current.pk == user.pk:
                        caps.update(MANAGER_CAPABILITIES)
            except Exception:
                pass

        profile['capabilities'] = sorted(caps)
        return Response(profile)


class PasswordChangeView(APIView):
    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({'detail': 'Password changed'})


class UserPagination(PageNumberPagination):
    page_size = 20


class UserListView(ListCreateAPIView):
    permission_classes = (HasCapability,)
    required_capability = 'user.view'
    serializer_class = UserListSerializer
    pagination_class = UserPagination

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            self.required_capability = 'user.create'
            self.serializer_class = UserCreateSerializer
        else:
            self.required_capability = 'user.view'
            self.serializer_class = UserListSerializer
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = User.objects.all().order_by('id')
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')
        if role:
            qs = qs.filter(role=role)
        if is_active is not None:
            if is_active.lower() in ('true', '1'):
                qs = qs.filter(is_active=True)
            else:
                qs = qs.filter(is_active=False)
        if search:
            qs = qs.filter(models.Q(username__icontains=search) | models.Q(email__icontains=search))
        return qs

    def create(self, request, *args, **kwargs):
        ser = UserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if User.objects.filter(username=ser.validated_data.get('username')).exists():
            return Response({'detail': 'username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=ser.validated_data.get('email')).exists():
            return Response({'detail': 'email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        user = ser.save()
        data = UserDetailSerializer(user).data
        temp = getattr(ser, '_temporary_password', None)
        if temp:
            data['temporary_password'] = temp
        return Response(data, status=status.HTTP_201_CREATED)


class UserDetailView(RetrieveUpdateAPIView):
    permission_classes = (HasCapability,)
    required_capability = 'user.view'
    serializer_class = UserDetailSerializer
    queryset = User.objects.all()


class UserDeactivateView(APIView):
    permission_classes = (HasCapability,)
    required_capability = 'user.deactivate'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        # check active manager for OPEN month
        from apps.months.models import ManagerAssignment, Month
        open_month = Month.objects.filter(status=Month.Status.OPEN).first()
        if open_month and ManagerAssignment.current_manager(open_month) and ManagerAssignment.current_manager(open_month).pk == user.pk:
            return Response({'code': 'cannot_deactivate_active_manager'}, status=status.HTTP_400_BAD_REQUEST)
        user.deactivate()
        return Response({'status': 'deactivated'})


class UserReactivateView(APIView):
    permission_classes = (HasCapability,)
    required_capability = 'user.deactivate'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = True
        user.save()
        return Response({'status': 'reactivated'})


class UserResetPasswordView(APIView):
    permission_classes = (HasCapability,)
    required_capability = 'user.reset_password'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        temp = generate_temp_password()
        user.set_password(temp)
        user.must_change_password = True
        user.save()
        return Response({'temporary_password': temp})

