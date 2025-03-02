import numpy as np
import cv2
import time
import pyautogui

WINDOW_NAME = 'Cheating'
WINDOW_SCALE = 0.25
MATCH_THRESHOLD = 0.6
DELAY = 0.5

try:
    import win32gui
    import win32con

    def set_window_topmost(window_title):
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

except ImportError:
    def set_window_topmost(window_title):
        print("win32gui not available, cannot set window topmost")
        pass


class CardMemoryHelper:
    def __init__(self, screenshot_path, card_back_path, card_templates, scale=WINDOW_SCALE):
        self.screenshot_path = screenshot_path
        self.card_back_path = card_back_path
        self.card_templates = card_templates
        self.scale = WINDOW_SCALE

        self.screenshot_color = cv2.imread(screenshot_path)
        self.screenshot_gray = cv2.cvtColor(self.screenshot_color,
                                            cv2.COLOR_BGR2GRAY)
        self.card_back = cv2.imread(card_back_path, cv2.IMREAD_GRAYSCALE)
        self.card_back_h, self.card_back_w = self.card_back.shape
        self.card_locations = self._find_all_cards()
        self.cheating_image = self.screenshot_color.copy()
        self.known_cards = {}
        self.pair_count = 0
        self.paired_cards = set()  # Keep track of paired cards (indices)
        self.pair_numbers = {} # Store pair number for each pair of indices


        self.window_width = int(self.screenshot_color.shape[1] * self.scale)
        self.window_height = int(self.screenshot_color.shape[0] * self.scale)

    def _find_all_cards(self):
        res = cv2.matchTemplate(self.screenshot_gray, self.card_back,
                                cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        card_locations = list(zip(*loc[::-1]))
        return card_locations

    def identify_card(self, card_index, new_screenshot_path):
        if not (0 <= card_index < len(self.card_locations)):
            return None

        x, y = self.card_locations[card_index]
        screenshot_color = cv2.imread(new_screenshot_path)
        card_roi = screenshot_color[y:y + self.card_back_h, x:x +
                                    self.card_back_w]
        card_roi_gray = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)

        best_match = None
        best_score = -1

        for card_name, template_path in self.card_templates.items():
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if template.shape != card_roi_gray.shape:
                template = cv2.resize(template, (self.card_back_w, self.card_back_h),
                                      interpolation=cv2.INTER_AREA)

            res = cv2.matchTemplate(card_roi_gray, template,
                                    cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            if max_val > best_score:
                best_score = max_val
                best_match = card_name

        if best_score > MATCH_THRESHOLD:
            return best_match
        else:
            return None

    def update_cheating_image(self, new_screenshot_path=None):
        newly_identified_cards = {}

        for card_index in range(len(self.card_locations)):
            if card_index not in self.known_cards:
                card_name = self.identify_card(card_index, new_screenshot_path)
                if card_name:
                    newly_identified_cards[card_index] = card_name


        for card_index, card_name in newly_identified_cards.items():
                self.known_cards[card_index] = card_name
                self.find_and_mark_pairs(card_index)  # Look for pairs after identifying new card
                x, y = self.card_locations[card_index]
                template_path = self.card_templates[card_name]
                card_image = cv2.imread(template_path)
                resized_card = cv2.resize(card_image, (self.card_back_w, self.card_back_h),
                                          interpolation=cv2.INTER_AREA)
                self.cheating_image[y:y + self.card_back_h, x:x +
                                    self.card_back_w] = resized_card


        # Update cheating image to show revealed cards and their pair numbers if paired
        for card_index, card_name in self.known_cards.items():
            x, y = self.card_locations[card_index]
            template_path = self.card_templates[card_name]
            card_image = cv2.imread(template_path)
            resized_card = cv2.resize(card_image, (self.card_back_w, self.card_back_h),
                                      interpolation=cv2.INTER_AREA)
            self.cheating_image[y:y + self.card_back_h, x:x +
                                self.card_back_w] = resized_card

        for card_index in self.paired_cards:
            if card_index in self.pair_numbers: # Ensure the pair number exists before drawing
                pair_number = self.pair_numbers[card_index]
                paired_indices = [i for i in self.paired_cards if i in self.pair_numbers and self.pair_numbers[i] == pair_number]
                if len(paired_indices) == 2: # Redraw numbers only if both parts of the pair are in paired_cards and have the same pair_number
                    index1, index2 = paired_indices
                    self.mark_pair(index1, index2, pair_number)


    def find_and_mark_pairs(self, newly_identified_index):
        """
        Finds if the newly identified card forms a pair with any other known, unpaired card.
        Marks the pair on the cheating image and updates paired_cards.
        """
        if newly_identified_index in self.paired_cards:  # Newly ID'd card is already paired.
            return

        new_card_name = self.known_cards[newly_identified_index]

        for existing_index, existing_card_name in self.known_cards.items():
            if existing_index != newly_identified_index and \
               existing_index not in self.paired_cards and \
               existing_card_name == new_card_name:

                # Found a Pair!
                self.pair_count += 1
                self.mark_pair(newly_identified_index, existing_index, self.pair_count)
                print(f"Found pair {self.pair_count}: Card {newly_identified_index} and Card {existing_index} are {new_card_name}")

                self.paired_cards.add(newly_identified_index)
                self.paired_cards.add(existing_index)
                self.pair_numbers[newly_identified_index] = self.pair_count # Assign pair number to each card in the pair
                self.pair_numbers[existing_index] = self.pair_count
                return  # Break after finding the first pair



    def mark_pair(self, index1, index2, pair_number):
        x1, y1 = self.card_locations[index1]
        x2, y2 = self.card_locations[index2]

        # Calculate center coordinates for text placement
        center_x1 = x1 + self.card_back_w // 2
        center_y1 = y1 + self.card_back_h // 2
        center_x2 = x2 + self.card_back_w // 2
        center_y2 = y2 + self.card_back_h // 2

        # Define text properties.
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 4.0
        font_color = (0, 0, 255)  # Red color
        thickness = 2

        # Add text to the cheating image
        cv2.putText(self.cheating_image, str(pair_number), (center_x1, center_y1), cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_color, thickness, cv2.LINE_AA)
        cv2.putText(self.cheating_image, str(pair_number), (center_x2, center_y2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_color, thickness, cv2.LINE_AA)

    def crop_cheating_image(self):
        if not self.card_locations:
            return None

        # find the box
        min_x = min(x for x, y in self.card_locations)
        min_y = min(y for x, y in self.card_locations)
        max_x = max(x + self.card_back_w for x, y in self.card_locations)
        max_y = max(y + self.card_back_h for x, y in self.card_locations)

        # Copy before cropping
        cropped_image = self.cheating_image[min_y:max_y, min_x:max_x].copy()
        return cropped_image

    # Remove the scale parameter from here
    def show_cheating_image(self, cropped_image=None):
        if cropped_image is not None:
            cheating_image_small = cv2.resize(cropped_image, (0, 0),  # Scale the Cropped Image
                                              fx=self.scale, fy=self.scale)
            cv2.imshow(WINDOW_NAME, cheating_image_small)
        elif self.cheating_image is not None:  # add this check
            cheating_image_small = cv2.resize(self.cheating_image, (0, 0),
                                              fx=self.scale, fy=self.scale)
            cv2.imshow(WINDOW_NAME, cheating_image_small)
        else:
            print("error")

    def get_card_coordinates(self, card_index):
        if 0 <= card_index < len(self.card_locations):
            return self.card_locations[card_index]
        else:
            return None

    def get_window_size(self):
        return self.window_width, self.window_height

    def reset_known_cards(self):
        """Resets the known_cards dictionary to start fresh."""
        self.known_cards = {}
        self.cheating_image = self.screenshot_color.copy()
        self.pair_count = 0
        self.paired_cards = set()
        self.pair_numbers = {}


if __name__ == "__main__":
    screenshot_path = "assets/screenshot.png"
    card_back_path = "assets/card_back.png"
    scale = 0.25

    card_templates = {
        "starfish": "assets/starfish.png",
        "ribbonfish": "assets/ribbonfish.png",
        "anglerfish": "assets/anglerfish.png",
        "molamola": "assets/molamola.png",
        "crab": "assets/crab.png",
        "shell": "assets/shell.png",
        "ray": "assets/ray.png",
        "jellyfish": "assets/jellyfish.png",
        "seahorse": "assets/seahorse.png"
    }
    helper = CardMemoryHelper(
        screenshot_path, card_back_path, card_templates, scale)

    window_width, window_height = helper.get_window_size()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, window_width, window_height)
    cv2.moveWindow(WINDOW_NAME, 0, 0)

    set_window_topmost(WINDOW_NAME)

    reset_flag = False  # Flag to indicate if a reset is requested

    try:
        while True:
            screenshot = pyautogui.screenshot()
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            new_screenshot_path = "current_screenshot.png"
            cv2.imwrite(new_screenshot_path, screenshot)

            if reset_flag:
                helper.reset_known_cards()
                reset_flag = False  # Reset the flag after performing the reset

            helper.update_cheating_image(new_screenshot_path)

            cropped_image = helper.crop_cheating_image()
            helper.show_cheating_image(cropped_image)

            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                break
            elif key & 0xFF == ord('r'):
                reset_flag = True  # Set the flag to trigger a reset

            time.sleep(DELAY)

    except KeyboardInterrupt:
        pass

    finally:
        cv2.destroyAllWindows()