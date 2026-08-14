import csv
import random
import datetime
import re


def load_commercials(csv_path='commercials.csv'):
    commercials = []
    with open(csv_path, newline='', encoding='utf-8', errors='ignore') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            duration = row.get('Duration', '').strip()
            if duration.isdigit():  # Check if duration is a valid integer
                row['Duration'] = int(duration)
                commercials.append(row)
            else:
                pass
    return commercials

# Stop when we're within this many seconds of the break (instead of requiring exact fit)
STOP_SLACK_SECONDS = 8

commercials = load_commercials()
last_played = {}
filler_bumper_played_times = []

def get_duration(path):
    try:
        return next(c['Duration'] for c in commercials if c['File Path'] == path)
    except StopIteration:
        return 0

def can_play_commercial(commercial, current_time, is_filler_bumper=False):
    four_hours_ago = current_time - datetime.timedelta(hours=4)
    last_played_time = last_played.get(commercial['File Name'])

    # Special handling for Toonami/filler bumper
    if is_filler_bumper:
        return (last_played_time is None or last_played_time < four_hours_ago) and filler_bumper_played_times.count(commercial['File Name']) < 2
    else:
        return last_played_time is None or last_played_time < four_hours_ago

def select_mixed_commercials(duration, types):
    current_time = datetime.datetime.now()
    mixed_commercials = []

    # ✅ Select commercials from each type, respecting duration limit
    # Pass duration so select_commercials filters by it
    for type in types:
        commercials_of_type = select_commercials(type, duration, [type])
        mixed_commercials.extend(commercials_of_type)

    # Shuffle to mix them up
    random.shuffle(mixed_commercials)

    # ✅ Now trim if we selected too much (should rarely happen now)
    total_duration = sum(get_duration_by_path(p) for p in mixed_commercials)
    while total_duration > duration and mixed_commercials:
        mixed_commercials.pop()
        total_duration = sum(get_duration_by_path(p) for p in mixed_commercials)

    return mixed_commercials


def select_commercials(channel, duration, types, fixed_number=1, played_commercials=set(), first_only=False):
    selected_commercials = []

    # ✅ FILTER by duration BEFORE selecting
    if duration and duration > 0:
        eligible_commercials = [c for c in commercials
                                if c['Type'] in types
                                and c['Channel/Block'] == channel
                                and c.get('Duration', 0) <= duration]
    else:
        # No duration limit
        eligible_commercials = [c for c in commercials if c['Type'] in types and c['Channel/Block'] == channel]

    if not eligible_commercials:
        return []  # nothing to choose from → prevent crash

    if fixed_number == 1:
        commercial = random.choice(eligible_commercials)
        selected_commercials.append(commercial)
        played_commercials.add(commercial['File Name'])
    else:
        while eligible_commercials and len(selected_commercials) < fixed_number:
            commercial = random.choice(eligible_commercials)
            selected_commercials.append(commercial)
            eligible_commercials.remove(commercial)
            played_commercials.add(commercial['File Name'])

    return [c['File Path'] for c in selected_commercials]


def get_duration_by_path(file_path):
    for c in commercials:
        if c['File Path'] == file_path:
            return c.get('Duration', 0)
    return 0

def get_commercials_for_show(channel_block, break_duration, first_show_in_block, is_last_part=False,
                             current_show=None, current_episode=None, next_show=None, next_episode=None,
                             current_block=None, next_block=None):
    selected_commercials = []
    if break_duration is None or break_duration == 0:
        break_duration = 160  # Default fallback

    target_time = break_duration
    total = 0
    # print(f"[COMM-START] block={channel_block} gap={break_duration} show={current_show} ep={current_episode}")

    try:
        if channel_block == "PowerHour":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Powerhouse Return', None, [current_show], fixed_number=1)
                if not return_bump:
                    return_bump = select_commercials('Powerhouse Return', None, ['General'], fixed_number=1)
                return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            promo_commercials = select_commercials('Powerhouse', None, ['Promo'], fixed_number=random.choice([1, 2]))
            indent_bumper = select_commercials('Powerhouse', None, ['indent'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Powerhouse Back', None, [current_show], fixed_number=1)
                if not back_bump:
                    back_bump = select_commercials('Powerhouse Back', None, ['General'], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 50
            attempts = 0

            # --- Fill remaining time with filler (smart, iterative fitting, no overshoot) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 50
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # === YOUR EXISTING PICK LOGIC (unchanged) ===
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 5):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(6, 7):  # only 6
                    candidate = select_commercials('Powerhouse', remaining_now,
                                                   [random.choice(['Special', 'Groove', 'shorties'])],
                                                   fixed_number=1)
                else:
                    candidate = select_commercials('Powerhouse', remaining_now, ['Promo'], fixed_number=1)
                # === end pick logic ===

                if not candidate:
                    continue

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than the time left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Allow exact fits and anything under the break
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    # Stop if we’re “close enough” to the end of the break
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # STOP_SLACK_SECONDS = 13
                        break
                else:
                    # Too long once everything is counted — try something else
                    continue

            # Add the filler we accumulated (do this ONCE, outside the loop)
            commercials_to_add.extend(filler_ads)
            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if "Toonami" == next_block:
                toonami_intro = select_commercials('Toonami', None, ['Intro'], fixed_number=1)
                if toonami_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(toonami_intro)
                    CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                    if CN_show_intro:
                        selected_commercials.extend(CN_show_intro)

                    filler_bumper_played_times.append('Toonami Intro')
            elif "Adult Swim" == next_block:
                As_intro = select_commercials('Adult Swim', break_duration, ['Intro'], first_only=True,
                                              fixed_number=1)
                # Check if an intro was added. If so, skip adding more commercials for this part.
                if As_intro:
                    selected_commercials.extend(As_intro)
                    return selected_commercials
            elif "Cartoon Theater" == next_block:
                CT_intro = select_commercials('Cartoon Theater', None, ['Intro'], fixed_number=1)
                # Check if an intro was added. If so, skip adding more commercials for this part.
                if CT_intro:
                    selected_commercials.extend(CT_intro)
                    return selected_commercials  # Return the list with only the intro

        elif channel_block == "Cartoon Network":

            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []
            CN_credit = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show != next_show and next_show is not None:
                CN_credit = select_commercials('Cartoon Network Credits', None, [current_show], fixed_number=1)
                if CN_credit:
                    selected_commercials.extend(CN_credit)

            return_bump_duration = sum(get_duration_by_path(path) for path in CN_credit)

            # --- Promos and Indent (go in the middle) ---
            promo_commercials = select_commercials('Cartoon Network', None, ['Promo'], fixed_number=random.choice([1, 2]))
            indent_bumper = select_commercials('Cartoon Network', None, ['City'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) ---

            back_bump = select_commercials('Cartoon Network', None, ['City'], fixed_number=1)
            back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 150
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 6):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(7, 8):
                    candidate = select_commercials('Powerhouse', remaining_now,
                                                   [random.choice(['Special', 'Groove', 'shorties'])],
                                                   fixed_number=1)
                else:
                    candidate = select_commercials('Cartoon Network', remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if "Toonami" == next_block:
                toonami_intro = select_commercials('Toonami', None, ['Intro'], fixed_number=1)
                if toonami_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(toonami_intro)
                    CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                    if CN_show_intro:
                        selected_commercials.extend(CN_show_intro)

                    filler_bumper_played_times.append('Toonami Intro')
            elif "Adult Swim" == next_block:
                As_intro = select_commercials('Adult Swim', break_duration, ['Intro'], first_only=True,
                                              fixed_number=1)
                # Check if an intro was added. If so, skip adding more commercials for this part.
                if As_intro:
                    selected_commercials.extend(As_intro)
                    return selected_commercials
            elif "Cartoon Theater" == next_block:
                CT_intro = select_commercials('Cartoon Theater', None, ['Intro'], fixed_number=1)
                # Check if an intro was added. If so, skip adding more commercials for this part.
                if CT_intro:
                    selected_commercials.extend(CT_intro)
                    return selected_commercials  # Return the list with only the intro
            elif "Miguzi" == next_block:
                mi_intro = select_commercials('Miguzi', None, ['intro'], fixed_number=1)
                if mi_intro:
                    selected_commercials.extend(mi_intro)
                    return selected_commercials

        elif channel_block == "Cartoon Theater":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if next_show == current_show:
                # If next_episode is exactly the next part, execute your code
                return_bump = select_commercials('Cartoon Theater', None, ['Return'], fixed_number=1)
                return_bump_to_add.extend(return_bump)



            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            promo_commercials = select_commercials('Cartoon Network', None, ['Promo'], fixed_number=random.choice([1, 2]))

            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) ---
            if current_show == next_show:
                back_bump = select_commercials('Cartoon Theater', None, ['Continues'], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 50
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 6):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(9, 9):
                    candidate = select_commercials('Powerhouse', remaining_now,
                                                   [random.choice(['Special', 'Groove'])],
                                                   fixed_number=1)
                elif pick_one in range(7, 7):
                    candidate = select_commercials('Cartoon Network', remaining_now, ['Promo'], fixed_number=1)
                elif pick_one in range(8, 8):
                    candidate = select_commercials('Toonami', remaining_now, ['Promo'], fixed_number=1)
                else:
                    candidate = select_commercials('Powerhouse', remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)

            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)


            if current_block != next_block:
                ending_commercial = select_commercials('Cartoon Theater', None, ['End'], fixed_number=1)
                if ending_commercial:
                    selected_commercials.extend(ending_commercial)

            if "Toonami" == next_block:
                toonami_intro = select_commercials('Toonami', None, ['Intro'], fixed_number=1)
                if toonami_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(toonami_intro)
                    CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                    if CN_show_intro:
                        selected_commercials.extend(CN_show_intro)
            elif "Miguzi" == next_block:
                mi_intro = select_commercials('Miguzi', None, ['intro'], fixed_number=1)
                if mi_intro:
                    selected_commercials.extend(mi_intro)
                    return selected_commercials

        elif channel_block == "Toonami":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []
            if current_show != next_show:
                toonami_credit = select_commercials('Toonami Credit', None, [current_show], fixed_number=1)
                if toonami_credit:
                    return_bump_to_add.extend(toonami_credit)
            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Toonami Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            egg = random.randint(1,2)
            if egg == 1:
                promo_commercials = select_commercials('Toonami', None, ['Promo'], fixed_number=1)
            else:
                promo_commercials = select_commercials('Toonami', None, ['Bumpers'], fixed_number=1)
            indent_bumper = select_commercials('Toonami', None, ['Filler'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Toonami Back', None, [current_show], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece - ✅ PASS remaining_now to filter by duration
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(5, 8):
                    candidate = select_commercials('Toonami', remaining_now, ['Promo'], fixed_number=1)
                else:
                    candidate = select_commercials("Cartoon Network", remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    continue  # ✅ Skip to next iteration instead of pass

                # Fallback: after many tries, attempt a generic short pool once
                if attempts in (10, 20, 30):
                    try:
                        fallback = select_mixed_commercials(remaining_now, ['General'])
                    except Exception:
                        fallback = None
                    if fallback:
                        candidate = fallback
                    else:
                        continue  # ✅ Skip if no fallback found

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_show != next_show:
                intro_bump = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                selected_commercials.extend(intro_bump)

            # Add Toonami ending if it's the last show in the block and this is the last part
            match = re.search(r" - part (\d+)$", current_episode)
            match2 = re.search(r" - part 1", current_episode)
            if match:
                if current_block != next_block and next_block != "Toonami Movie":
                    part_number = int(match.group(1))
                    ending_commercial = select_commercials('Toonami', None, ['Ending'], fixed_number=1)
                    selected_commercials.extend(ending_commercial)
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        if "Cartoon Network" == next_block:
                            CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)
                            if CN_show_intro:
                                selected_commercials.extend(CN_show_intro)
            elif match2:
                pass
            else:
                if "Cartoon Network" == next_block:
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)

                        if CN_show_intro:
                            selected_commercials.extend(CN_show_intro)

        elif channel_block == "Toonami Movie":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Toonami Return', None, [current_show], fixed_number=1)
                return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            egg = random.randint(1,2)
            if egg == 1:
                promo_commercials = select_commercials('Toonami', None, ['Promo'], fixed_number=1)
            else:
                promo_commercials = select_commercials('Toonami', None, ['Bumpers'], fixed_number=1)
            indent_bumper = select_commercials('Toonami', None, ['Filler'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Toonami Back', None, [current_show], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 20
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(5, 8):
                    candidate = select_commercials('Toonami', remaining_now, ['Promo'], fixed_number=1)
                else:
                    candidate = select_commercials("Cartoon Network", remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_show != next_show:
                intro_bump = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                selected_commercials.extend(intro_bump)

            # Add Toonami ending if it's the last show in the block and this is the last part
            match = re.search(r" - part (\d+)$", current_episode)
            match2 = re.search(r" - part 1", current_episode)
            if match:
                if current_block != next_block and next_block != "Toonami":
                    part_number = int(match.group(1))
                    ending_commercial = select_commercials('Toonami', None, ['Ending'], fixed_number=1)
                    selected_commercials.extend(ending_commercial)
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        if "Cartoon Network" == next_block:
                            CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)
                            if CN_show_intro:
                                selected_commercials.extend(CN_show_intro)
            elif match2:
                pass
            else:
                if "Cartoon Network" == next_block:
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)

                        if CN_show_intro:
                            selected_commercials.extend(CN_show_intro)

        elif channel_block == "Miguzi":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Miguzi Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)
                else:
                    return_bump = select_commercials('Miguzi Return', None, ['General'], fixed_number=1)
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Miguzi', None, ['promo'], fixed_number=1)


            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Miguzi Back', None, [current_show], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 50
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 7):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(8, 9):
                    candidate = select_commercials('Miguzi', remaining_now, ['promo'], fixed_number=1)
                else:
                    candidate = select_commercials("Cartoon Network", remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_show != next_show:
                intro_bump = select_commercials('Miguzi Intro', None, ['Next Show'], fixed_number=1)
                selected_commercials.extend(intro_bump)

            if current_block != next_block:
                ending_commercial = select_commercials('Miguzi', None, ['outro'], fixed_number=1)
                selected_commercials.extend(ending_commercial)

                if "Toonami" == next_block or "Toonami Movie" == next_block:
                    toonami_intro = select_commercials('Toonami', None, ['Intro'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                        if CN_show_intro:
                            selected_commercials.extend(CN_show_intro)

                        filler_bumper_played_times.append('Toonami Intro')
                elif "Cartoon Network" == next_block:
                        toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                        if toonami_intro:
                            # Add the intro to the selected commercials
                            selected_commercials.extend(toonami_intro)
                            CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)

                            if CN_show_intro:
                                selected_commercials.extend(CN_show_intro)

        elif channel_block == "Adult Swim":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Adult Swim Done', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)
                else:
                    return_bump = select_commercials('Adult Swim Return', None, [current_show], fixed_number=1)
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            egg = random.randint(1,3)
            if egg == 1:
                promo_commercials = select_commercials('Adult Swim', None, ['Static'], fixed_number=1)
            else:
                promo_commercials = select_commercials('Adult Swim', None, ['Bump'], fixed_number=1)
            indent_bumper = select_commercials('Adult Swim', None, ['Text'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Adult Swim Back', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Adult Swim', None, ['Static'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)


            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 80
            attempts = 0
            type_limit_tracker = {
                'Text': 0
            }
            MAX_PER_TYPE = {
                'Text': 2
            }
            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1


                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])
                elif pick_one in range(6, 10):
                    candidate = select_commercials('Adult Swim', remaining_now, ['Promo'], fixed_number=1)
                else:
                    if type_limit_tracker['Text'] < MAX_PER_TYPE['Text']:
                        candidate = select_commercials('Adult Swim', None, ['Text'], fixed_number=1)
                        if candidate:
                            type_limit_tracker['Text'] += 1
                    else:
                        continue  # skip and try something else

                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            if current_show !=next_show:
                oonami_commercial4 = select_commercials('Adult Swim Next', None, [next_show], fixed_number=1)
                if oonami_commercial4:
                    commercials_to_add.extend(oonami_commercial4)

            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_show != next_show:
                intro_bump = select_commercials('Adult Swim Intro', None, [next_show], fixed_number=1)
                selected_commercials.extend(intro_bump)

        elif channel_block == "SVES":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            if current_show != next_show:
                toonami_credit = select_commercials('Toonami Credit', None, [current_show], fixed_number=1)
                if toonami_credit:
                    selected_commercials.extend(toonami_credit)
                toonami_return = select_commercials('SVES Done', None, [current_show], fixed_number=1)
                if toonami_return:
                    selected_commercials.extend(toonami_return)

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('SVES Back', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)
                return_bump2 = select_commercials('Watching', None, [current_show], fixed_number=1)
                if return_bump2 and not return_bump:
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('SVES', None, ['Promo'], fixed_number=1)
            if current_show != next_show:

                indent_bumper = select_commercials('SVES Next', None, [next_show], fixed_number=1)
                if indent_bumper:
                    commercials_to_add.extend(indent_bumper)

            commercials_to_add.extend(promo_commercials)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('SVES Return', None, [current_show], fixed_number=1)
                back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 120
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(5, 6):
                    candidate = select_commercials('Toonami', remaining_now, ['Promo'], fixed_number=1)
                elif pick_one in range(7, 8):
                    candidate = select_commercials('SVES', remaining_now, ['Promo'], fixed_number=1)
                else:
                    candidate = select_commercials("Cartoon Network", remaining_now, ['Promo'], fixed_number=1)

                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration :
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_show != next_show:
                intro_bump = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
                selected_commercials.extend(intro_bump)

            # Add Toonami ending if it's the last show in the block and this is the last part
            match = re.search(r" - part (\d+)$", current_episode)
            match2 = re.search(r" - part 1", current_episode)
            if match:
                if current_block != next_block and next_block != "Toonami Movie":
                    part_number = int(match.group(1))
                    ending_commercial = select_commercials('Toonami', None, ['Ending'], fixed_number=1)
                    selected_commercials.extend(ending_commercial)
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        if "Cartoon Network" == next_block:
                            CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)
                            if CN_show_intro:
                                selected_commercials.extend(CN_show_intro)
            elif match2:
                pass
            else:
                if "Cartoon Network" == next_block:
                    ending_commercial = select_commercials('Toonami', None, ['Ending'], fixed_number=1)
                    selected_commercials.extend(ending_commercial)
                    toonami_intro = select_commercials('Cartoon Network', None, ['Start'], fixed_number=1)
                    if toonami_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(toonami_intro)
                        CN_show_intro = select_commercials('Cartoon Network Intro', None, [next_show], fixed_number=1)

                        if CN_show_intro:
                            selected_commercials.extend(CN_show_intro)

        elif channel_block == 'Playhouse Disney':
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Play House Disney', None, ['Bump'], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Play House Disney', None, ['Promo'], fixed_number=1)
            indent_bumper = select_commercials('Play House Disney', None, ['Bump'], fixed_number=1)


            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show != next_show:
                back_bump = select_commercials('Play House Disney Next', None, [next_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0
            used_commercials = set()  # ✅ Track used commercials to prevent duplicates

            while attempts < max_attempts:
                attempts += 1

                # Calculate time left to fill
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # ✅ Use Playhouse Disney's own commercial pools with duration filter
                candidate = select_commercials('Play House Disney', remaining_now, ['Promo'], fixed_number=1)


                # Last resort: try a Playhouse Disney bump
                if not candidate:
                    candidate = select_commercials('Play House Disney', remaining_now, ['Bump'], fixed_number=1)

                if not candidate:
                    continue

                # ✅ Check for duplicates
                candidate_paths = set(candidate)
                if candidate_paths & used_commercials:
                    continue  # Skip if already used

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # ✅ Hard check: never exceed remaining time
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )


                # ✅ NEVER overfill - accept underfill instead
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break  # Close enough, stop filling

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if next_show != current_show:
                if next_block == current_block:
                    DM_intro = select_commercials('Play House Disney Intro', None, [next_show], fixed_number=1)
                    if DM_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(DM_intro)

            # Shuffle the commercials to mix up the order
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == 'Disney':
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Disney Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Disney', None, ['promos'], fixed_number=1)
            indent_bumper = select_commercials('Disney', None, ['wand id'], fixed_number=1)
            if current_show != next_show:
                indent_bumper2 = select_commercials('Disney', None, [next_show], fixed_number=1)
                if indent_bumper2:
                    commercials_to_add.extend(indent_bumper2)
            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Disney Back', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting, no overshoot) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            failed_mixed_attempts = 0  # ✅ Track failed attempts with mixed commercials

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # 1) Try mixed pools first, but only if we haven't failed too many times
                if failed_mixed_attempts < 10:
                    candidate = select_mixed_commercials(remaining_now, [
                        'Pets', 'Sports', 'Songs', 'showstuff', 'Movie goers',
                        'Mikes', 'learning', 'express', '411'
                    ])
                else:
                    candidate = []  # ✅ Force fallback to promos after 10 failed attempts


                if not candidate:
                    # allow promos as lightweight filler FIRST
                    candidate = select_commercials('Disney', None, ['promos'], fixed_number=1) or candidate
                if not candidate:
                    # last resort: one bump (if you allow it)
                    candidate = select_commercials('Disney', None, ['bump'], fixed_number=1) or candidate
                if not candidate:
                    continue  # nothing this round, try again

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left
                if candidate_duration > remaining_now:
                    failed_mixed_attempts += 1  # ✅ Increment failed counter
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Accept exact/under fills; stop once we’re “close enough”
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # e.g., 13
                        break
                else:
                    continue  # too long once counted; try another option

            # Add the filler we accumulated (once, outside the loop)
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if "Disney Movie" == next_block:
                DM_intro = select_commercials('Disney', None, ['MovieIntro'], fixed_number=1)
                if DM_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(DM_intro)

            if next_show != current_show:
                if next_block == current_block:
                    DM_intro = select_commercials('Disney', None, ['originalBUmp'], fixed_number=1)
                    if DM_intro:
                        # Add the intro to the selected commercials
                        selected_commercials.extend(DM_intro)

        elif channel_block == "Disney Movie":

            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Disney Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Disney', None, ['promos'], fixed_number=1)
            indent_bumper = select_commercials('Disney', None, ['wand id'], fixed_number=1)
            if current_show != next_show:
                indent_bumper2 = select_commercials('Disney', None, [next_show], fixed_number=1)
                if indent_bumper2:
                    commercials_to_add.extend(indent_bumper2)
            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            # ------ BAck bump -------
            if current_show == next_show:
                back_bump = select_commercials('Disney Back', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Disney Back', None, ['Movie'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)


            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting, no overshoot) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # === YOUR PICK LOGIC (unchanged) ===
                candidate = select_mixed_commercials(remaining_now, [
                    'Pets', 'Sports', 'Songs', 'showstuff', 'Movie goers',
                    'Mikes', 'learning', 'express', '411'
                ])
                # === end pick logic ===


                if not candidate:
                    continue

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Accept exact/under fills
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    # Close enough stop (≤ 13s slack after a successful append)
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # e.g., 13
                        break
                else:
                    # Too long once everything is counted — try another option
                    continue

            # Add the filler we accumulated (once, outside the loop)
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == 'Toon Disney' or channel_block == 'Toon Disney Movie':
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Toon Disney Back', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Toon disney', None, ['Promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)



            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Toon Disney Return', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one == 6:
                    candidate = select_mixed_commercials(remaining_now, ['Pets', 'Sports', 'Songs', 'showstuff', 'Movie goers',
                    'Mikes', 'learning', 'express', '411'])
                else:
                    candidate = select_commercials('Toon Disney', remaining_now, ['promo'], fixed_number=1)

                if not candidate:
                    pass
                # Fallback: after many tries, attempt a generic short pool once (still obeys remaining_now)


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # ✅ NEVER overfill - accept underfill instead
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if "Disney Movie" == next_block:
                DM_intro = select_commercials('Disney', None, ['MovieIntro'], fixed_number=1)
                if DM_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(DM_intro)
            elif "Jetix" == next_block:
                DM_intro = select_commercials('Jetix', None, ['intro'], fixed_number=1)
                if DM_intro:
                    # Add the intro to the selected commercials
                    selected_commercials.extend(DM_intro)

        elif channel_block == "Nick Jr":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []
            ending_to_add = []
            id_to_add = []


            jrid = select_commercials('NickJR', None, ['ID'], fixed_number=1)
            id_to_add.extend(jrid)
            # --- Return bump (ALWAYS FIRST) ---
            if current_block == next_block:

                ioo = random.randint(1,2)
                if ioo == 1:
                    return_bump = select_commercials('FACE', None, ['Back'], fixed_number=1)
                    return_bump_to_add.extend(return_bump)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Nick Jr', None, ['promo'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if next_block == current_block:
                id_commercial = select_commercials('NickJR', None, ['ID'], fixed_number=1)
                selected_commercials.extend(id_commercial)

                back_bump = select_commercials('Face Next', None, [next_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Face Next', None, ['Generic'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)

            else:
                toonami_commercial = select_commercials('NickJR', None, ['end'], fixed_number=1)
                ending_to_add.extend(toonami_commercial)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 40
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 2)
                if pick_one == 1:
                    candidate = select_mixed_commercials(remaining_now, ['Toys'])
                else:
                    candidate = select_commercials("Nick", remaining_now, ['promo'], fixed_number=1)

                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(id_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            selected_commercials.extend(back_bump_to_add)
            if ending_to_add:
                selected_commercials.extend(ending_to_add)

        elif channel_block == "NICK" or channel_block == "Nick Movie":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                return_bump = select_commercials('Nick Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)
                else:
                    return_bump = select_commercials('Nick Return', None, ['Generic'], fixed_number=1)
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Nick', None, ['promo'], fixed_number=1)
            if next_show == "The Wild Thornberrys" or next_show == "KaBlam!":
                indent_bumper = select_commercials('Nick Next', None, [next_show], fixed_number=1)
                if indent_bumper:
                    commercials_to_add.extend(indent_bumper)

            commercials_to_add.extend(promo_commercials)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Nick Back', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Nick Back', None, ['Generic'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0
            max_bumps = 2
            bumps = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(5, 6):
                    candidate = select_commercials('Nick', remaining_now, ['coms'], fixed_number=1)
                elif pick_one in range(7, 9):
                    candidate = select_commercials('Nick', remaining_now, ['promo'], fixed_number=1)
                else:
                    if max_bumps > bumps:
                        candidate = select_commercials("Nick", remaining_now, ['bump'], fixed_number=1)
                        bumps += 1
                    else:
                        continue

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total > break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if "Nick Jr" == next_block:
                mi_intro = select_commercials('NickJR', None, ['intro'], fixed_number=1)
                if mi_intro:
                    selected_commercials.extend(mi_intro)
                    return selected_commercials

        elif channel_block == "Nick at Nite":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Nick at nite', None, ['Promo'], fixed_number=1)
            if next_show != current_show:
                indent_bumper = select_commercials('Nick at Nite Next', None, [next_show], fixed_number=1)
                if indent_bumper:
                    commercials_to_add.extend(indent_bumper)

            commercials_to_add.extend(promo_commercials)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_commercials("Nick at nite", remaining_now, ['Promo'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not kids', 'General'])
                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "Fox":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            pattern = re.escape(current_episode) + r" - part (\d+)$"
            if re.match(pattern, next_episode):
                return_bump = select_commercials('Fox Return', None, [current_show], fixed_number=1)
                if return_bump:
                    return_bump_to_add.extend(return_bump)
                else:
                    return_bump = select_commercials('Fox Return', None, ['General'], fixed_number=1)
                    return_bump_to_add.extend(return_bump)

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('FoxBox', None, ['promo'], fixed_number=1)
            if next_show != current_show:
                indent_bumper = select_commercials('Fox Next', None, [next_show], fixed_number=1)
                if indent_bumper:
                    commercials_to_add.extend(indent_bumper)

            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if re.match(pattern, next_episode):
                if current_show == next_show:
                    back_bump = select_commercials('Fox Back', None, [current_show], fixed_number=1)
                    back_bump_to_add.extend(back_bump)
                else:
                    # The condition matches your criteria
                    back_bump = select_commercials('Fox Back', None, ['General'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 50
            attempts = 0

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # Try a small filler piece
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 7):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                else:
                    candidate = select_commercials('FoxBox', remaining_now, ['promo'], fixed_number=1)

                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration + 10:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

        elif channel_block == "Fox Prime" or channel_block == "Fox Movie" or channel_block == 'House':
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Fox', None, ['promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting, no overshoot) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0
            failed_mixed_attempts = 0  # ✅ Track failed attempts with mixed commercials

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                pick_one = random.randint(1, 10)
                if pick_one == 3:
                    candidate = select_commercials("Fox", remaining_now, ['promo'], fixed_number=1)
                elif pick_one == 5:
                    candidate = select_mixed_commercials(remaining_now, ['Games'])
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'General'])

                if not candidate:
                    continue  # nothing this round, try again

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Accept exact/under fills; stop once we’re “close enough”
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # e.g., 13
                        break
                else:
                    continue  # too long once counted; try another option

            # Add the filler we accumulated (once, outside the loop)
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "Kids WB":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                Wb_return = select_commercials('Kids WB Return', None, [current_show], fixed_number=1)
                if Wb_return:
                    return_bump_to_add.extend(Wb_return)
                # else:
                WB_show_bumper = select_commercials('Kids WB Bump', None, [current_show], fixed_number=1)
                if WB_show_bumper:
                    return_bump_to_add.extend(WB_show_bumper)
                else:
                    first_bumper = select_commercials('Kids WB Bump', None, ['General'], fixed_number=1)
                    return_bump_to_add.extend(first_bumper)
            else:
                WB_show_bumper = select_commercials('Kids WB Bump', None, [next_show], fixed_number=1)
                if WB_show_bumper:
                    return_bump_to_add.extend(WB_show_bumper)
                else:
                    first_bumper = select_commercials('Kids WB Bump', None, ['General'], fixed_number=1)
                    return_bump_to_add.extend(first_bumper)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---
            egg = random.randint(1, 2)
            if egg == 1:
                promo_commercials = select_commercials('Kids WB', None, ['promo'], fixed_number=1)
            else:
                promo_commercials = select_commercials('Kids WB', None, ['Bump'], fixed_number=1)
            if current_show != next_show:
                indent_bumper = select_commercials('Kids WB Next', None, [next_show], fixed_number=1)
                if indent_bumper:
                    commercials_to_add.extend(indent_bumper)

            commercials_to_add.extend(promo_commercials)


            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                back_bump = select_commercials('Kids WB Back', None, [current_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Kids WB Back', None, ['General'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)
            else:
                back_bump = select_commercials('Kids WB Bump', None, [next_show], fixed_number=1)
                if back_bump:
                    back_bump_to_add.extend(back_bump)
                else:
                    back_bump = select_commercials('Kids WB Back', None, ['General'], fixed_number=1)
                    back_bump_to_add.extend(back_bump)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting, no overshoot) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 45
            attempts = 0

            type_limit_tracker = {
                'Bump': 0
            }
            MAX_PER_TYPE = {
                'Bump': 1
            }

            while attempts < max_attempts:
                # Recalc time left; do NOT early-stop here for slack
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                # NOTE: no STOP_SLACK_SECONDS check here; we only stop after a successful append
                remaining_now = (
                    break_duration
                    - sum(get_duration_by_path(p) for p in return_bump_to_add)
                    - sum(get_duration_by_path(p) for p in commercials_to_add)
                    - filler_total_duration
                    - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break
                    break
                attempts += 1

                # How much time we can still fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # === YOUR EXISTING PICK LOGIC (unchanged) ===
                pick_one = random.randint(1, 10)
                if pick_one in range(1, 4):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                elif pick_one in range(5, 9):
                    candidate = select_commercials('Kids WB', remaining_now, ['Promo'], fixed_number=1)
                else:
                    if type_limit_tracker['Bump'] < MAX_PER_TYPE['Bump']:
                        candidate = select_commercials('Kids WB', None, ['Bump'], fixed_number=1)
                        if candidate:
                            type_limit_tracker['Bump'] += 1
                    else:
                        continue
                # === end pick logic ===

                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue

                # Hard guard: never pick longer than time left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    # Close enough: stop if leftover ≤ STOP_SLACK_SECONDS (13s)
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break
                else:
                    # Too long once everything is counted — try another pick
                    continue

            commercials_to_add.extend(filler_ads)
            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

            if current_block != next_block:
                intro_bump = select_commercials('Kids WB', None, ['Ending'], fixed_number=1)
                selected_commercials.extend(intro_bump)

        elif channel_block == "WB Prime":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('WB', None, ['promos'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_commercials("WB", remaining_now, ['promos'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Accept exact/under fills; stop once we’re “close enough”
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # e.g., 13
                        break
                else:
                    continue  # too long once counted; try another option

            # Add the filler we accumulated (once, outside the loop)
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "WB Day" or channel_block == 'Xena':
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('WB', None, ['promos'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_commercials("WB", remaining_now, ['promos'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, [ 'Games', 'General'])

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left
                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                # Accept exact/under fills; stop once we’re “close enough”
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration

                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:  # e.g., 13
                        break
                else:
                    continue  # too long once counted; try another option

            # Add the filler we accumulated (once, outside the loop)
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "ABC":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('ABC', None, ['promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one in range(2,4):
                    candidate = select_commercials("ABC", remaining_now, ['promo'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Games', 'General'])
                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block in ["ABC Prime", "Kyle XY", "Whos Line", "ABC Movie"]:
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('ABC', None, ['promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            # --- Fill remaining time with filler (smart, iterative fitting) ---
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 70
            attempts = 0

            while attempts < max_attempts:
                attempts += 1

                # Time left to fill right now
                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in return_bump_to_add)
                        - sum(get_duration_by_path(p) for p in commercials_to_add)  # indent + promo already here
                        - filler_total_duration
                        - sum(get_duration_by_path(p) for p in back_bump_to_add)
                )
                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one in range(2, 4):
                    candidate = select_commercials("ABC", remaining_now, ['promo'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'General'])
                if not candidate:
                    pass

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "ABC Jetix":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                Wb_return = select_commercials('ABC Jetix Back', None, [current_show], fixed_number=1)
                if Wb_return:
                    return_bump_to_add.extend(Wb_return)
                else:
                    first_bumper = select_commercials('ABC Jetix Back', None, ['Generic'], fixed_number=1)
                    return_bump_to_add.extend(first_bumper)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('ABC Jetix', None, ['promo'], fixed_number=1)
            indent_bumper = select_commercials('ABC Jetix', None, ['Indent'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                Wb_return = select_commercials('ABC Jetix Return', None, [current_show], fixed_number=1)
                if Wb_return:
                    back_bump_to_add.extend(Wb_return)
                else:
                    first_bumper = select_commercials('ABC Jetix Return', None, ['Generic'], fixed_number=1)
                    back_bump_to_add.extend(first_bumper)


            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 9)
                if pick_one in range(1, 6):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                else:
                    candidate = select_commercials('ABC Jetix', remaining_now, ['promo'], fixed_number=1)
                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

        elif channel_block == "Jetix":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Return bump (ALWAYS FIRST) ---
            if current_show == next_show:
                Wb_return = select_commercials('Jetix Return', None, [current_show], fixed_number=1)
                if Wb_return:
                    return_bump_to_add.extend(Wb_return)
                else:
                    first_bumper = select_commercials('Jetix Return', None, ['Generic'], fixed_number=1)
                    return_bump_to_add.extend(first_bumper)


            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Jetix', None, ['promo'], fixed_number=1)
            indent_bumper = select_commercials('Jetix', None, ['Indent'], fixed_number=1)

            commercials_to_add.extend(promo_commercials)
            commercials_to_add.extend(indent_bumper)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Back bump (ALWAYS LAST) if same show continues ---
            if current_show == next_show:
                Wb_return = select_commercials('Jetix Back', None, [current_show], fixed_number=1)
                if Wb_return:
                    back_bump_to_add.extend(Wb_return)
                else:
                    first_bumper = select_commercials('Jetix Back', None, ['Generic'], fixed_number=1)
                    back_bump_to_add.extend(first_bumper)


            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 9)
                if pick_one in range(3, 6):
                    candidate = select_mixed_commercials(remaining_now, ['Toys', 'Games', 'General'])
                else:
                    candidate = select_commercials('Jetix', remaining_now, ['promo'], fixed_number=1)
                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration
            total_final_duration = return_bump_duration + middle_duration + filler_duration + back_bump_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(return_bump_to_add)
            selected_commercials.extend(commercials_to_add)
            if back_bump_to_add:
                selected_commercials.extend(back_bump_to_add)

        elif channel_block == "Comedy Central":
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Comedy Central', None, ['promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_commercials('Comedy Central', remaining_now, ['promo'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])
                if not candidate:
                    pass


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration+1:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block in ["Sci-Fi","Sci-Fi Anime", "Sci-Fi Movie"]:
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            return_bump_duration = sum(get_duration_by_path(path) for path in return_bump_to_add)

            # --- Promos and Indent (go in the middle) ---

            promo_commercials = select_commercials('Sci-Fi', None, ['promo'], fixed_number=1)
            commercials_to_add.extend(promo_commercials)

            middle_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            back_bump_duration = sum(get_duration_by_path(path) for path in back_bump_to_add)

            # --- Compute current duration with first and last included ---
            current_duration = return_bump_duration + middle_duration + back_bump_duration
            filler_needed = break_duration - current_duration

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_commercials("Sci-Fi", remaining_now, ['promo'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])


                candidate_duration = sum(get_duration_by_path(p) for p in candidate)
                if candidate_duration > remaining_now:
                    continue
                if candidate_duration > remaining_now:
                    continue
                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add) - middle_duration

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block in ["ANIME","OVA"]:
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])
                else:
                    candidate = select_commercials("Anime Trailer", remaining_now, ['promo'], fixed_number=1)

                if not candidate:
                    # Normal pool has nothing that fits remaining_now.
                    # Try a short clip — select_commercials will only return one if its Duration <= remaining_now.
                    candidate = select_commercials("Anime Trailer", remaining_now, ['short'], fixed_number=1)
                    if candidate:
                        filler_ads.extend(candidate)
                        filler_total_duration += sum(get_duration_by_path(p) for p in candidate)
                    # Either way, we're done filling this break.
                    break

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            remaining_after = (
                break_duration
                - filler_total_duration
            )

            if random.randint(1,20) == 3:
                if 0 < remaining_after <= 13:
                    short_clip = select_commercials("Anime Trailer", remaining_after, ['short'], fixed_number=1)
                    if short_clip:
                        filler_ads.extend(short_clip)
                        filler_total_duration += sum(get_duration_by_path(p) for p in short_clip)


            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block in ["Anime Movie"]:
            return_bump_to_add = []
            commercials_to_add = []
            back_bump_to_add = []

            # --- Fill remaining time with filler (smart, iterative fitting) ---
            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # Try a small filler piece
                pick_one = random.randint(1, 7)
                if pick_one == 3:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])
                else:
                    candidate = select_commercials("Anime Trailer", remaining_now, ['promo'], fixed_number=1)

                if not candidate:
                    # Normal pool has nothing that fits remaining_now.
                    # Try a short clip — select_commercials will only return one if its Duration <= remaining_now.
                    candidate = select_commercials("Anime Trailer", remaining_now, ['short'], fixed_number=1)
                    if candidate:
                        filler_ads.extend(candidate)
                        filler_total_duration += sum(get_duration_by_path(p) for p in candidate)
                    # Either way, we're done filling this break.
                    break

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                if candidate_duration > remaining_now:
                    continue

                projected_total = (
                        sum(get_duration_by_path(p) for p in return_bump_to_add)
                        + sum(get_duration_by_path(p) for p in commercials_to_add)
                        + filler_total_duration
                        + candidate_duration
                        + sum(get_duration_by_path(p) for p in back_bump_to_add)
                )

                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                    if projected_total >= break_duration:
                        break  # close enough
                else:
                    continue  # too long, try something smaller

            remaining_after = (
                break_duration
                - filler_total_duration
            )
            if 0 < remaining_after <= 13:
                short_clip = select_commercials("Anime Trailer", remaining_after, ['short'], fixed_number=1)
                if short_clip:
                    filler_ads.extend(short_clip)
                    filler_total_duration += sum(get_duration_by_path(p) for p in short_clip)


            # Add best attempt filler
            commercials_to_add.extend(filler_ads)

            filler_duration = sum(get_duration_by_path(path) for path in commercials_to_add)

            # --- Final order: RETURN → shuffled middle → BACK ---
            random.shuffle(commercials_to_add)
            selected_commercials.extend(commercials_to_add)

        elif channel_block == "Infomercial":

            # --- Fill remaining time with filler (smart, iterative fitting) ---

            commercials_to_add = []
            filler_ads = []
            filler_total_duration = 0
            max_attempts = 100
            attempts = 0

            while attempts < max_attempts:
                attempts += 1
                # Time left to fill right now

                remaining_now = (
                        break_duration
                        - sum(get_duration_by_path(p) for p in commercials_to_add)
                        - filler_total_duration
                )

                if remaining_now <= 0:
                    break

                # === Your existing pick logic (fixed only for typos) ===

                pick_one = random.randint(1, 20)

                if pick_one == 3:
                    candidate = select_commercials("NFO", None, ['Info'], fixed_number=1)
                else:
                    candidate = select_mixed_commercials(remaining_now, ['Not Kids', 'Games', 'General'])

                # === end pick logic ===

                candidate_duration = sum(get_duration_by_path(p) for p in candidate)

                # Hard guard: never pick longer than what's left

                if candidate_duration > remaining_now:
                    continue
                projected_total = filler_total_duration + candidate_duration

                # Allow exact fits and anything under the break
                if projected_total <= break_duration:
                    filler_ads.extend(candidate)
                    filler_total_duration += candidate_duration
                    # Stop if we’re “close enough” (≤ 13s slack after a successful append)
                    slack = break_duration - projected_total
                    if 0 <= slack <= STOP_SLACK_SECONDS:
                        break

                else:

                    # Too long once everything is counted — try another option

                    continue

            # Add the filler we accumulated (once, outside the loop)

            commercials_to_add.extend(filler_ads)

            # --- Final order (Infomercial has no head/tail bumpers) ---

            random.shuffle(commercials_to_add)

            selected_commercials.extend(commercials_to_add)

        elif channel_block == "No":
            pass

        elif channel_block == "Miguzi Intro":
            mi_intro = select_commercials('Miguzi', None, ['intro'], fixed_number=1)
            if mi_intro:
                selected_commercials.extend(mi_intro)
                return selected_commercials
        elif channel_block == "Toonami Intro":
            toonami_intro = select_commercials('Toonami', None, ['Intro'], fixed_number=1)
            selected_commercials.extend(toonami_intro)
            CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
            if CN_show_intro:
                selected_commercials.extend(CN_show_intro)
        elif channel_block == "Adult Swim Intro":
            As_intro = select_commercials('Adult Swim', break_duration, ['Intro'], fixed_number=1)
            # Check if an intro was added. If so, skip adding more commercials for this part.
            if As_intro:
                selected_commercials.extend(As_intro)
        elif channel_block == "SVES Intro":
            toonami_intro = select_commercials('SVES', None, ['Intro'], fixed_number=1)
            selected_commercials.extend(toonami_intro)
            CN_show_intro = select_commercials('Toonami Intro', None, [next_show], fixed_number=1)
            if CN_show_intro:
                selected_commercials.extend(CN_show_intro)
        elif channel_block == "Kids WB Intro":
            WB_intro = select_commercials('Kids WB', break_duration, ['Intro'], fixed_number=1)
            selected_commercials.extend(WB_intro)
        elif channel_block == "Cartoon Theater Intro":
            CT_intro = select_commercials('Cartoon Theater', None, ['Intro'], fixed_number=1)
            # Check if an intro was added. If so, skip adding more commercials for this part.
            if CT_intro:
                selected_commercials.extend(CT_intro)
        elif channel_block == "Disney Movie Intro":
            DM_intro = select_commercials('Disney', None, ['MovieIntro'], fixed_number=1)
            if DM_intro:
                # Add the intro to the selected commercials
                selected_commercials.extend(DM_intro)



    except Exception as e:
        print(f"[COMM-ERROR] {current_show} - {current_episode} "
              f"(block={channel_block}, gap={break_duration}) | {e}")
    return selected_commercials


