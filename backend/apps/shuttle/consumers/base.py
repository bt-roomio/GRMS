import asyncio
import logging
import traceback

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from jwt import ExpiredSignatureError
from jwt import decode as jwt_decode
from jwt.exceptions import DecodeError

from rest_framework.fields import ValidationError

from core.utils.snake_case import convert_to_snake
from shuttle.utils.response import response
from users.utils.get_user import get_user

logger = logging.getLogger("django")


class BaseConsumer(AsyncJsonWebsocketConsumer):
    """
    BaseConsumer provides a WebSocket consumer with built-in support for
    JSON message processing, authentication checking, and managing periodic tasks.

    It extends AsyncJsonWebsocketConsumer to handle JSON messages and integrates
    utilities for converting key naming styles, user authentication via JWT tokens,
    and scheduling periodic tasks.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the BaseConsumer instance.

        Sets up internal dictionaries to manage commands, periodic tasks, and the authenticated user.
        Also initializes flags to track expired token errors.
        """
        super().__init__(*args, **kwargs)
        self.auth_cmd = {}
        self.cmds = {}
        self.tasks = {}
        self.expired_token_error_sent = False
        self.user = None

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """
        Receives a JSON message over the WebSocket connection, processes it, checks authentication,
        and delegates further handling to the JSON message receiver.

        This method performs the following:
          - Decodes the incoming JSON text data.
          - Processes the message by converting keys from camelCase to snake_case.
          - Saves command data from the message.
          - Checks for valid authentication.
          - Calls `receive_json` with the processed data.

        In the event of errors (such as token expiration, decode errors, or validation issues),
        the method sends an appropriate error response and stops any periodic tasks if needed.

        Args:
            text_data (str): The text data received from the WebSocket.
            bytes_data (bytes, optional): The binary data received from the WebSocket.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If the message is empty or not properly structured.
            ExpiredSignatureError: If the authentication token has expired.
            DecodeError: If decoding the JWT or JSON fails.
        """
        try:
            data = await self.process_message(await self.decode_json(text_data))
            await self.save_cmd(data)
            await self.check_auth(data)
            await self.receive_json(data, **kwargs)

        except ExpiredSignatureError as err:
            if not self.expired_token_error_sent:
                await self.send_json(response({}, 0, 401, str(err)))
            self.expired_token_error_sent = True
            await self.stop_all_periodic_tasks()

        except DecodeError as err:
            await self.send_json(response({}, self.auth_cmd.get("cmd_id"), 400, str(err)))

        except ValueError as err:
            await self.send_json(response({}, None, 400, str(err)))

        except Exception as err:
            tb = traceback.format_exc()
            logger.warning(f"Error occurred: {err}")
            logger.warning(f"Traceback: {tb}")
            await self.send_json(response({}, None, 500, str(err)))

    async def check_auth(self, data={}):
        """
        Validates the authentication token and sets the authenticated user.

        This method decodes the JWT token provided in the authentication command using the secret key,
        retrieves the corresponding user, and ensures the user has an associated tenant.
        If valid command data is provided, it resumes tasks using stored command data.

        Args:
            data (dict, optional): Additional command data that may include an authentication command.

        Raises:
            ValidationError: If the authenticated user does not have a tenant.
        """
        checked_token = jwt_decode(self.auth_cmd.get("token", ""), settings.SECRET_KEY, algorithms=["HS256"])
        self.user = await get_user(checked_token)

        if not self.user.tenant_id:
            raise ValidationError("User doesn't have tenant!")

        # Resume tasks from cmds if valid auth_cmd token is provided
        if data and data.get("auth_cmd", {}).get("token"):
            data["cmds"] = self.cmds.values()

        self.expired_token_error_sent = False

    async def save_cmd(self, data):
        """
        Saves command data from the incoming message into internal storage.

        Extracts a list of commands (if provided) and the authentication command,
        then updates the consumer's command and authentication dictionaries.

        Args:
            data (dict): The processed message data containing 'cmds' and optionally 'auth_cmd'.
        """
        if isinstance(data, dict):
            cmds = data.get("cmds")
            if isinstance(cmds, list):
                for cmd in cmds:
                    self.cmds[cmd.get("cmd_id")] = cmd

            auth_cmd = data.get("auth_cmd") or self.auth_cmd
            self.auth_cmd = auth_cmd

    async def process_message(self, message):
        """
        Asynchronously processes a message by validating its structure and converting its keys
        from camelCase to snake_case.

        This function performs the following steps:
          - Verifies that the input `message` is not empty.
          - Checks that `message` is a dictionary.
          - Ensures that the 'cmds' key in the message is associated with a list.
          - Converts all keys in the message from camelCase to snake_case using the `convert_to_snake` utility.

        Args:
            message (dict): The message dictionary to process. Must contain a key 'cmds' with a list value.

        Raises:
            ValueError: If the message is empty.
            ValueError: If the message is not a dictionary.
            ValueError: If the 'cmds' key is not a list.

        Returns:
            dict: A new dictionary with all keys converted to snake_case.
        """
        if not message:
            raise ValueError("Message cannot be empty.")
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary.")
        if not isinstance(message["cmds"], list):
            raise ValueError("The 'cmds' field must be a list.")

        return convert_to_snake(message)

    async def disconnect(self, code):
        """
        Handles the WebSocket disconnection by stopping all periodic tasks and performing cleanup.

        Args:
            code (int): The disconnection code.
        """
        await self.stop_all_periodic_tasks()
        await super().disconnect(code)

    async def start_periodic_task(self, func, cmd, task_name, *args, **kwargs):
        """
        Starts a periodic task that executes an asynchronous function at regular intervals.

        This method creates a loop that periodically calls the specified async function with the given command
        and additional arguments. It cancels any existing task with the same name before starting a new one.
        If an error occurs during execution (including expired tokens), the task is cancelled and an error
        response is sent.

        Args:
            func (coroutine): The asynchronous function to execute periodically.
            cmd (dict): The command data associated with the periodic task.
            task_name (str): A unique identifier for the periodic task.
            *args: Positional arguments to pass to the async function.
            **kwargs: Keyword arguments to pass to the async function.

        Returns:
            asyncio.Task: The periodic task that was created.

        Notes:
            The interval for periodic execution is determined by the 'time_window' in the command's 'history_cmd'
            field, defaulting to 5 seconds if not provided.
        """
        interval = cmd.get("history_cmd", {}).get("time_window") or 5

        await self.cancel_task(task_name)

        async def periodic_loop():
            try:
                while not self.expired_token_error_sent:
                    try:
                        await self.validate_auth()
                        res = await func(cmd, *args, **kwargs)
                        await self.send_json(res)

                    except ExpiredSignatureError as err:
                        await self.send_json(response({}, 0, 401, str(err)))
                        self.expired_token_error_sent = True
                        await self.cancel_task(task_name)

                    except Exception as exc:
                        await self.send_json(f"Ошибка в периодической задаче '{task_name}': {exc}")
                        await self.cancel_task(task_name)

                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Периодическая задача '%s' отменена", task_name)
                raise

        task = asyncio.create_task(periodic_loop())
        self.tasks[task_name] = task
        return task

    async def stop_all_periodic_tasks(self):
        """
        Cancels all running periodic tasks and clears the task registry.

        Iterates over all tasks stored in the consumer, cancels each one,
        and clears the tasks dictionary to reset the state.
        """
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()

    async def cancel_task(self, task_key):
        """
        Cancels a specific periodic task identified by its key.

        If a task with the specified key exists, it is cancelled,
        removed from the task registry, and a warning is logged.

        Args:
            task_key (str): The unique key identifying the task to cancel.
        """
        if self.tasks.get(task_key):
            self.tasks[task_key].cancel()
            del self.tasks[task_key]
            logger.warning(f"Периодическая задача '{task_key}' отменена")

    async def validate_auth(self):
        """
        Validates the presence and validity of the authentication token.

        This method checks for the token in the authentication command. If the token is missing,
        it raises an ExpiredSignatureError. It also decodes the token to ensure its validity.

        Raises:
            ExpiredSignatureError: If the authentication token is missing or invalid.
        """
        if not self.auth_cmd.get("token"):
            raise ExpiredSignatureError("Missing authentication token.")
        jwt_decode(self.auth_cmd.get("token", ""), settings.SECRET_KEY, algorithms=["HS256"])
