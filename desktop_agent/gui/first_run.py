import dearpygui.dearpygui as dpg
import requests
import json
import os
import re
import logging
import time
import uuid
from typing import Callable

logger = logging.getLogger(__name__)

class FirstRunWindow:
    def __init__(self, server_url: str, on_success: Callable[[str, str, str], None]):
        """Initialize the First Run window."""
        self.server_url = server_url
        self.on_success = on_success
        self.manager_uuid = ""
        self.client_uuid = None
        self.token = None
        self.registration_complete = False
        self.error_message = ""
        self.is_loading = False
        self.max_retries = 3
        self.current_retry = 0

    def is_valid_uuid(self, uuid_str):
        """Validate UUID format."""
        if not uuid_str:
            return False
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))

    def register_client(self):
        """Register a client with the server."""
        try:
            if not self.manager_uuid:
                self.error_message = "Please enter manager UUID"
                return False

            if not self.is_valid_uuid(self.manager_uuid):
                self.error_message = "Invalid UUID format. Use format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                return False

            # Get computer name or use username if not available
            computer_name = os.environ.get('COMPUTERNAME', os.environ.get('USERNAME', 'Unknown'))

            # Create client registration request
            response = requests.post(
                f"{self.server_url}/api/clients/",
                json={
                    'manager_uuid': self.manager_uuid,
                    'name': computer_name
                },
                timeout=10
            )

            # Check response
            if response.status_code in [201, 200]:  # Accept both new registration and already registered
                data = response.json()
                self.client_uuid = data.get('uuid')
                
                if not self.client_uuid:
                    self.error_message = "Server did not return client UUID"
                    return False

                # Get token from response
                self.token = data.get('token')
                if not self.token:
                    self.error_message = "Server did not return authentication token"
                    return False

                if response.status_code == 201:
                    logger.info(f"Client registered successfully: {self.client_uuid}")
                else:
                    logger.info(f"Client already registered: {self.client_uuid}")
                return True
            else:
                # Registration error
                logger.error(f"Registration error: {response.status_code} - {response.text}")
                self.error_message = f"Registration error: {response.text}"
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {self.server_url}")
            self.error_message = f"Connection error to server: {self.server_url}"
            return False
        except Exception as e:
            logger.error(f"Error registering client: {e}")
            self.error_message = f"Error: {str(e)}"
            return False

    def run(self):
        """Run the First Run window."""
        try:
            # Initialize DearPyGui
            dpg.create_context()
            dpg.create_viewport(title="Process Sentinel - First Run", width=500, height=250)

            # Create the window
            with dpg.window(label="First Run Setup", tag="primary_window", width=380, height=230, no_resize=True):
                dpg.add_text("Welcome to Process Sentinel!")
                dpg.add_text("Enter your manager's UUID to continue:")
                dpg.add_input_text(label="Manager UUID", width=300, tag="uuid_input")
                dpg.add_text("UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", color=(200, 200, 200))
                dpg.add_button(label="Save and Continue", tag="save_button")
                dpg.add_text("", tag="error_text", color=(255, 0, 0))
                dpg.add_text("", tag="status_text", color=(0, 200, 0))

            # Setup and show viewport
            dpg.setup_dearpygui()
            dpg.show_viewport()

            # Center the window
            dpg.set_primary_window("primary_window", True)
            viewport_width = dpg.get_viewport_client_width()
            viewport_height = dpg.get_viewport_client_height()
            window_width = 380
            window_height = 230
            x = (viewport_width - window_width) // 2
            y = (viewport_height - window_height) // 2
            dpg.set_item_pos("primary_window", [x, y])

            # Main event loop
            while dpg.is_dearpygui_running():
                # Process events and render
                dpg.render_dearpygui_frame()

                # Check for button press
                if dpg.is_item_clicked("save_button") and not self.is_loading:
                    # Get the UUID from the input field
                    self.manager_uuid = dpg.get_value("uuid_input")

                    # Try to register with the server
                    self.is_loading = True
                    dpg.set_value("error_text", "")
                    dpg.set_value("status_text", "Connecting to server...")
                    dpg.configure_item("save_button", enabled=False)

                    if self.register_client():
                        dpg.set_value("status_text", "Registration successful! Starting application...")
                        self.registration_complete = True
                        time.sleep(1)  # Give user time to see the success message
                        break
                    else:
                        self.current_retry += 1
                        if self.current_retry >= self.max_retries:
                            dpg.set_value("error_text", f"Maximum retries reached. Please restart the application.")
                            dpg.set_value("status_text", "")
                            time.sleep(2)
                            break
                        else:
                            dpg.set_value("error_text", f"{self.error_message} (Attempt {self.current_retry}/{self.max_retries})")
                            dpg.set_value("status_text", "")
                            dpg.configure_item("save_button", enabled=True)
                            self.is_loading = False

                # Small sleep to prevent CPU usage
                time.sleep(0.01)

        except Exception as e:
            logger.error(f"Error in first run window: {e}")
            self.error_message = f"Error: {str(e)}"
        finally:
            # Clean up DearPyGui
            dpg.destroy_context()

            # If registration was successful, call the success callback
            if self.registration_complete:
                self.on_success(self.manager_uuid, self.client_uuid, self.token)
            else:
                # Если регистрация не удалась, запускаем окно заново
                first_run = FirstRunWindow(self.server_url, self.on_success)
                first_run.run() 