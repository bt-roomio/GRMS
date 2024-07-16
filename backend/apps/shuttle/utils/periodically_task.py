# import asyncio

# from django.conf import settings
# from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
# from jwt import decode as jwt_decode
# from shuttle.utils.response import response


# async def periodically_task(seconds: int, self, func, *args):
#     while True:
#         try:
#             authCmd = self.context.get("authCmd", {})
#             token = authCmd.get("token")

#             if not authCmd:
#                 await self.send_json(response({}, 0, 401, "Token is invalid or expired!"))
#                 return

#             if authCmd and token:
#                 checked_token = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])

#             self.context.update({"has_expired": False})
#             await func(*args)
#             await asyncio.sleep(seconds)

#         except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError) as err:
#             self.context.update({"has_expired": True})
#             await self.send_json(response({}, 0, 401, str(err)))
#             return
