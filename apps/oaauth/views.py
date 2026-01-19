from datetime import datetime
from rest_framework.views import APIView
from .serializer import LoginSerializer, UserSerializer
from .authentications import generate_jwt
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializer import RestPwdSerializer

# Create your views here.
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.last_login = datetime.now()
            user.save()
            token = generate_jwt(user)
            return Response({'token': token, 'user': UserSerializer(user).data})
        else:
            # print(serializer.errors)
            detail = list(serializer.errors.values())[0][0]
            #drf返回非200时，它的错误参数叫detail
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

# class AuthenticatedRequired:
#     permission_classes = [IsAuthenticated]

class RestPwdView(APIView):
    def post(self, request):
        serializer = RestPwdSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            pwd1 = serializer.validated_data['pwd1']
            request.user.set_password(pwd1)
            request.user.save()
            return Response()
        else:
            print(serializer.errors)
            detail = list(serializer.errors.values())[0][0]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

