"""The ten DataCenterBench Tier 1 tasks, copied from Robocurve's benchmark release 1.0.0.

Instruction, name and rubric (guidance and levels) are exactly as released: the judges' prompt is built from them,
so a change to any of them is a new task version and a new release. Rubric scores 0 and 1 stay integers, as in the
release, because the prompt prints them ("Score 1", not "Score 1.0"). Equipment keeps what an outside lab needs to
build the setup (product, link, how it was used); purchase records stay with Robocurve.
"""

from __future__ import annotations

from dataclasses import dataclass

RELEASE = "1.0.0"
"""The Robocurve benchmark release these tasks come from."""


@dataclass(frozen=True)
class Level:
    """One rubric level: the score and the end state that earns it."""

    score: float
    description: str


@dataclass(frozen=True)
class Rubric:
    """A task's rubric: guidance for the judges and the levels, the only scores allowed."""

    guidance: str
    levels: tuple[Level, ...]

    @property
    def scores(self) -> tuple[float, ...]:
        """The allowed trial scores, highest first (as released)."""
        return tuple(level.score for level in self.levels)


@dataclass(frozen=True)
class Equipment:
    """An object the task needs: the product the published runs used and how it was used."""

    name: str
    quantity: int
    url: str | None
    note: str | None


@dataclass(frozen=True)
class RealWorld:
    """The data-center procedure step the task stands in for, with its source."""

    step: str
    procedure: str
    quote: str
    source_title: str | None
    source_url: str | None
    locator: str | None
    simplified: str


@dataclass(frozen=True)
class TaskSpec:
    """One task: what the model is told, how the board is set, and how a trial is scored."""

    key: str
    release_id: str
    name: str
    version: int
    instruction: str
    setup: str
    reset: str
    rubric: Rubric
    equipment: tuple[Equipment, ...]
    photos: tuple[str, str, str]
    real_world: RealWorld
    keypad_code: str | None = None

    def judge_task(self) -> dict[str, object]:
        """The task as the published judges read it: id, name, guidance and levels."""
        return {
            "id": self.release_id,
            "name": self.name,
            "guidance": self.rubric.guidance,
            "levels": [
                {"score": lv.score, "description": lv.description} for lv in self.rubric.levels
            ],
        }


SPECS: tuple[TaskSpec, ...] = (
    TaskSpec(
        key="unplug",
        release_id="DC-unplug",
        name="Unplug the charger from the power strip",
        version=1,
        instruction="Unplug the white phone charger from the white power strip.",
        setup="Power strip fixed to the board. White phone charger fully plugged into the same outlet every trial.",
        reset="Push the charger fully back into the same outlet.",
        rubric=Rubric(
            guidance="",
            levels=(
                Level(
                    score=1,
                    description="The charger is completely out of the power strip, resting on the board or table.",
                ),
                Level(score=0, description="The charger is still in an outlet, even if loosened."),
            ),
        ),
        equipment=(
            Equipment(
                name="White phone charger and white power strip (on hand, not part of the bench order)",
                quantity=1,
                url=None,
                note=None,
            ),
        ),
        photos=(
            "docs/assets/unplug-setup-top.jpg",
            "docs/assets/unplug-setup-left.jpg",
            "docs/assets/unplug-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Disconnect server power",
            procedure="Disconnect the power cable from the power supply, then press the release latch and slide the unit out.",
            quote="Disconnect the power cable from the power source and from the PSU you intend to remove.",
            source_title="Dell EMC PowerEdge R440 installation and service manual (Rev. A11)",
            source_url="https://dl.dell.com/topicspdf/poweredge-r440_owners-manual9_en-us.pdf",
            locator="Removing a power supply unit, p. 99",
            simplified="We remove a phone charger from a power strip. The real procedure disconnects a flexible power cord at the source and the server supply.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="knob",
        release_id="DC-knob",
        name="Turn the knob to the mark",
        version=1,
        instruction="Turn the round knob on the white box clockwise until the black line on it points at the black mark on the box.",
        setup="Rotary dimmer in a surface backbox, fixed to the board. A black line is drawn on the knob like a clock hand. One black mark on the box at the start position and one at the goal (fully clockwise). The knob starts at the start mark every trial.",
        reset="Turn the knob back counterclockwise until its line points at the start mark.",
        rubric=Rubric(
            guidance="The knob carries a black line like a clock hand. Compare where it points with the start photos and with the marks on the box.",
            levels=(
                Level(
                    score=1,
                    description="The line on the knob points at the goal mark (turned clockwise to it).",
                ),
                Level(
                    score=0.5,
                    description="The knob turned clockwise noticeably but the line stops short of the goal mark.",
                ),
                Level(
                    score=0,
                    description="The knob did not turn clockwise (unchanged, or turned the other way).",
                ),
            ),
        ),
        equipment=(
            Equipment(
                name="Leviton Trimatron rotary dimmer, RNL06-10Z, white",
                quantity=1,
                url="https://www.amazon.com/dp/B073H9Y7SH",
                note="Black line drawn on the knob; start and goal marks drawn on the box.",
            ),
            Equipment(
                name="Leviton surface-mount backbox, single gang, 42777-1WA, white",
                quantity=1,
                url="https://www.amazon.com/dp/B0028CIC8U",
                note=None,
            ),
        ),
        photos=(
            "docs/assets/knob-setup-top.jpg",
            "docs/assets/knob-setup-left.jpg",
            "docs/assets/knob-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Set a UPS bypass selector",
            procedure="Turn a rack-mount maintenance bypass rotary switch from UPS to MAINS, after checking the MAINS lamp is lit.",
            quote="Transfer the rotary switch from UPS to MAINS, provided the MAINS lamp is illuminated",
            source_title="Vertiv Liebert MicroPOD installer/user guide",
            source_url="https://www.vertiv.com/49ecbb/globalassets/products/critical-power/uninterruptible-power-supplies-ups/liebert-micropod-maintenance-bypass-and-output-distribution-accessory2/liebert-micropod-230v-user-guide.pdf",
            locator="§6.1, p. 11",
            simplified="Our dimmer turns between drawn marks. The real selector has fixed positions and requires checking an indicator before switching.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="toggle",
        release_id="DC-toggle",
        name="Flip the light switch",
        version=1,
        instruction="Flip the lever of the light switch on the white box to the other side.",
        setup="Wall toggle switch in its box, fixed to the board; tip of the lever colored black. Lever on the same side every trial.",
        reset="Flip the lever back to its start side.",
        rubric=Rubric(
            guidance="The lever tip is colored black. Compare which side of its slot it points to in the start and end photos.",
            levels=(
                Level(
                    score=1,
                    description="The lever is on the other side of its slot compared with the start.",
                ),
                Level(score=0, description="The lever is on the same side as at the start."),
            ),
        ),
        equipment=(
            Equipment(
                name="Leviton 15 A toggle switch, single pole, 1451-2W, white",
                quantity=1,
                url="https://www.amazon.com/dp/B00002NAR0",
                note="Leviton toggle switch",
            ),
            Equipment(
                name="Leviton surface-mount backbox, single gang, 42777-1WA, white",
                quantity=1,
                url="https://www.amazon.com/dp/B0028CIC8U",
                note="Leviton single-gang surface backbox",
            ),
        ),
        photos=(
            "docs/assets/toggle-setup-top.jpg",
            "docs/assets/toggle-setup-left.jpg",
            "docs/assets/toggle-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Operate UPS bypass breakers",
            procedure="Move a UPS to maintenance bypass: close the bypass breaker, then open the input breaker, in the order the manual gives.",
            quote="8. Close the MBB. … 10. Open the MIB.",
            source_title="Vertiv Liebert EXM UPS user manual (SL-26100 Rev 12)",
            source_url="https://www.vertiv.com/4a0511/globalassets/shared/liebert-exm-20-200kva-ups-um-en-na-sl-26100_rev-12-lt.pdf",
            locator="§7.6, p. 53",
            simplified="Our wall switch tests moving a lever between two positions. It omits the breaker mechanism, electrical checks and switching sequence.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="key",
        release_id="DC-key",
        name="Turn the key",
        version=1,
        instruction="Turn the key clockwise to its other position. Leave it there and release it.",
        setup="Key switch in its white box, fixed to the board; key in its start position, the same every trial.",
        reset="Turn the key back to its start position.",
        rubric=Rubric(
            guidance="The top camera looks down on the key's head: compare its angle in the start and end photos. The instruction also asks the robot to let go of the key.",
            levels=(
                Level(
                    score=1,
                    description="The key is turned clockwise to its other position and left there, with the gripper released.",
                ),
                Level(
                    score=0.5,
                    description="The key is turned to its other position but the gripper is still holding it.",
                ),
                Level(
                    score=0,
                    description="The key is in its start position (or turned the other way).",
                ),
            ),
        ),
        equipment=(
            Equipment(
                name="APIELE 22 mm two-position key switch, XB2-10Y/21 (maintained)",
                quantity=1,
                url="https://www.amazon.com/dp/B088PRMK7R",
                note=None,
            ),
            Equipment(
                name="uxcell push-button control station box, 22 mm, one hole",
                quantity=1,
                url="https://www.amazon.com/dp/B07WQQQGFX",
                note="uxcell one-hole 22 mm enclosure",
            ),
        ),
        photos=(
            "docs/assets/key-setup-top.jpg",
            "docs/assets/key-setup-left.jpg",
            "docs/assets/key-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Release a breaker interlock",
            procedure="Release the key interlock on the maintenance bypass breaker before switching it.",
            quote="Insert the Key into the lock on the MBB and turn the Key.",
            source_title="Vertiv Liebert EXM UPS user manual (SL-26100 Rev 12)",
            source_url="https://www.vertiv.com/4a0511/globalassets/shared/liebert-exm-20-200kva-ups-um-en-na-sl-26100_rev-12-lt.pdf",
            locator="§7.6, p. 53",
            simplified="Our key starts in a panel switch. We test turning it, without inserting the key or operating the associated breaker.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="cover",
        release_id="DC-cover",
        name="Open the spring-loaded cover",
        version=1,
        instruction="Lift the clear cover on the grey box all the way open, until it stays open on its own. It is spring-loaded and snaps shut if it is not pushed far enough.",
        setup="E-stop box fixed to the board in front of the left arm; clear cover closed, red button released (pulled up), the same every trial.",
        reset="Close the clear cover. Check the red button is released (pulled up), not latched down.",
        rubric=Rubric(
            guidance="The clear cover is hinged at the back. Closed, it lies flat over the red button. Open, it stands up behind the button on its own. The overhead and left wrist cameras both show it. The end photos are taken with the arms parked, so a cover only held up by the gripper will have snapped shut.",
            levels=(
                Level(score=1, description="The cover is open and staying open on its own."),
                Level(score=0, description="The cover is closed."),
            ),
        ),
        equipment=(
            Equipment(
                name="GUETNEU emergency-stop button with cover, IP67 switch box",
                quantity=1,
                url="https://www.amazon.com/dp/B0CR19ZTBJ",
                note="GUETNEU covered emergency-stop button box",
            ),
        ),
        photos=(
            "docs/assets/cover-setup-top.jpg",
            "docs/assets/cover-setup-left.jpg",
            "docs/assets/cover-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Access an emergency power-off button",
            procedure="In an emergency, rotate the clear protective cover and push the Emergency Power Off switch on the power distribution unit's panel.",
            quote="rotate the clear protective cover and push the Emergency Power Off (EPO) switch",
            source_title="Vertiv Liebert FPC user manual",
            source_url="https://www.vertiv.cn/globalassets/products/critical-power/power-distribution/liebert-fpc-15-300kva-with-vpmp-user-manual_00.pdf",
            locator="§4.1.1",
            simplified="We score opening the cover until it stays open. Pressing the button and shutting down equipment are outside this task.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="slider",
        release_id="DC-slider",
        name="Move the slider to the other line",
        version=1,
        instruction="Move the small slider on the white dimmer from the black line it is on to the other black line.",
        setup="Slide dimmer in its box, fixed to the board. Two black lines on the plate mark the start and the end of the move (short of the hard end stop, which needs extra force). Slider on the start line every trial; large rocker switch unchanged.",
        reset="Slide the slider back to the start line. Leave the large rocker switch as it is.",
        rubric=Rubric(
            guidance="The slider is the small dark control on the white dimmer; two black lines on the plate mark where it starts and where it should end. Compare its position with the start photos.",
            levels=(
                Level(
                    score=1,
                    description="The slider reached the other black line (at it or past it).",
                ),
                Level(
                    score=0.5,
                    description="The slider moved noticeably toward the other line but stopped short of it.",
                ),
                Level(
                    score=0,
                    description="The slider did not move toward the other line, or the large rocker switch was changed.",
                ),
            ),
        ),
        equipment=(
            Equipment(
                name="Leviton SureSlide dimmer, 6672-1LW, white",
                quantity=1,
                url="https://www.amazon.com/dp/B00CF4IPGK",
                note=None,
            ),
            Equipment(
                name="Leviton 1-gang Decora wallplate, 122-80401-NW, white",
                quantity=1,
                url="https://www.amazon.com/dp/B000HEHCE6",
                note="Leviton Decora wallplate",
            ),
            Equipment(
                name="Leviton surface-mount backbox, single gang, 42777-1WA, white",
                quantity=1,
                url="https://www.amazon.com/dp/B0028CIC8U",
                note="Leviton single-gang surface backbox",
            ),
        ),
        photos=(
            "docs/assets/slider-setup-top.jpg",
            "docs/assets/slider-setup-left.jpg",
            "docs/assets/slider-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Select a UPS operating mode",
            procedure="During a UPS restart, slide the mode selector left to engage static bypass, then back right to UPS.",
            quote="Use the slide switch to set the UPS to Static Bypass. Slide the switch to the left to engage Static Bypass.",
            source_title="Liebert UPStation S3 user manual (discontinued model)",
            source_url="https://www.vertiv.com/globalassets/products/critical-power/uninterruptible-power-supplies-ups/discontinued---liebert-upstation-s3/liebert-upstation-s3-user-manual.pdf",
            locator="§3.2.4, p. 44",
            simplified="Our dimmer slides between drawn marks. The cited UPS has a two-position mode selector and is a discontinued model.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="keypad",
        release_id="DC-keypad",
        name="Enter a code on the keypad",
        version=1,
        instruction="Type 52 on the number pad and nothing else. The iPhone next to it shows what you type.",
        setup="USB number pad and the iPhone display on the board, the phone on a MagSafe stand; starting a trial clears the display.",
        reset="None by hand: starting a trial clears the display. Before each automatic start, the rig software checks the scene against a reference photo, that the motors have cooled, and that the phone shows a test word (READY).",
        rubric=Rubric(
            guidance="The iPhone next to the number pad shows what was typed. One keypress away means one character missing, one extra, or one wrong (for example 5, 582 or 53). The trial is scored from the display's own log; the judges cross-check it.",
            levels=(
                Level(score=1, description="The display reads exactly 52."),
                Level(
                    score=0.5,
                    description="The display is one keypress away from 52: one character missing, one extra, or one wrong.",
                ),
                Level(score=0, description="The display shows anything else, or nothing."),
            ),
        ),
        equipment=(
            Equipment(
                name="TechGarden wired USB number pad, 19 keys, black",
                quantity=1,
                url="https://www.amazon.com/dp/B0BNPVMQVT",
                note=None,
            ),
            Equipment(
                name="iPhone on a MagSafe charging stand, showing the keypad page",
                quantity=1,
                url=None,
                note=None,
            ),
        ),
        photos=(
            "docs/assets/keypad-setup-top.jpg",
            "docs/assets/keypad-setup-left.jpg",
            "docs/assets/keypad-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Log in on a UPS control panel",
            procedure="Log in on a UPS's hand-held control panel by pressing its physical keys: CLEAR, PROGRAM, the password digits, then ENTER.",
            quote="To enter the user-level password, follow these steps: [CLEAR] [PROGRAM] [3] [7] [7] [ENTER]",
            source_title="Eaton FERRUPS FE/QFE UPS user's guide (164201404 Rev C)",
            source_url="https://www.eaton.com/content/dam/eaton/products/backup-power-ups-surge-it-power-distribution/backup-power-ups/eaton-ferrups-tower-ups/eaton-ferrups-FE-QFE-userguide-.pdf",
            locator="Entering Passwords, p. 30",
            simplified="We use a two-digit code on a USB number pad, with an iPhone display. The real panel requires a longer key sequence.",
        ),
        keypad_code="52",
    ),
    TaskSpec(
        key="plug",
        release_id="DC-plug",
        name="Plug the charger into the power strip",
        version=1,
        instruction="Pick up the white phone charger and plug it into one of the outlets on the white power strip. Push it in until the prongs are fully inserted.",
        setup="Power strip fixed to the board, outlets up. White phone charger standing loose next to it, same spot and orientation every trial.",
        reset="Pull the charger out and stand it back in its spot, same orientation.",
        rubric=Rubric(
            guidance="Fully seated means no metal of the prongs is visible between the charger and the strip.",
            levels=(
                Level(
                    score=1,
                    description="The charger is fully plugged into an outlet: flush against the strip, no prong metal visible.",
                ),
                Level(
                    score=0.5,
                    description="The charger is in an outlet and stays there, but not fully: a visible gap or tilt.",
                ),
                Level(score=0, description="The charger is not in an outlet."),
            ),
        ),
        equipment=(
            Equipment(
                name="White phone charger and white power strip (on hand, not part of the bench order)",
                quantity=1,
                url=None,
                note=None,
            ),
        ),
        photos=(
            "docs/assets/plug-setup-top.jpg",
            "docs/assets/plug-setup-left.jpg",
            "docs/assets/plug-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Reconnect server power",
            procedure="Reconnect the power cord to a newly installed server power supply and secure it with the strap.",
            quote="Connect the power cable to the PSU, and plug the cable into a power outlet.",
            source_title="Dell EMC PowerEdge R440 installation and service manual (Rev. A11)",
            source_url="https://dl.dell.com/topicspdf/poweredge-r440_owners-manual9_en-us.pdf",
            locator="Installing a power supply unit, p. 100",
            simplified="We insert a phone charger into a power strip. The real procedure connects a flexible power cord to the supply and a power outlet.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="join",
        release_id="DC-join",
        name="Join the Ethernet plug and coupler",
        version=1,
        instruction="Use one hand to hold the Ethernet coupler and the other to insert the Ethernet plug into it until it clicks into place.",
        setup="Ethernet cable and a loose Ethernet coupler on the board, same spots every trial.",
        reset="Pull the plug out of the coupler and put both back in their spots.",
        rubric=Rubric(
            guidance="",
            levels=(
                Level(
                    score=1,
                    description="The Ethernet plug is fully inserted into the coupler, no gap.",
                ),
                Level(score=0, description="The plug is not fully inserted in the coupler."),
            ),
        ),
        equipment=(
            Equipment(
                name="Amazon Basics Cat 6 Ethernet patch cable, 3 ft, black",
                quantity=1,
                url="https://www.amazon.com/dp/B089MGH8T5",
                note="Amazon Basics 3 ft Cat6 cable",
            ),
            Equipment(
                name="EZYUMM RJ45 Ethernet coupler, female to female, 3-pack",
                quantity=1,
                url="https://www.amazon.com/dp/B0D5ZHG8JX",
                note="EZYUMM Ethernet coupler",
            ),
        ),
        photos=(
            "docs/assets/join-setup-top.jpg",
            "docs/assets/join-setup-left.jpg",
            "docs/assets/join-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Mate equipment connectors",
            procedure="Connect the UPS and distribution-box cable connectors together and make sure they are fully mated.",
            quote="connect the UPS and distribution box connectors together. Ensure that the connectors are fully connected.",
            source_title="Vertiv Liebert GXT5 UPS installer/user guide",
            source_url="https://www.vertiv.com/4a3d0a/globalassets/shared/liebert-gxt5-installer-user-guide-120-208v-input-l1-l2-n-g-120-208v-output-mv-sl-70524.pdf",
            locator="§3.6.2, p. 22",
            simplified="Our task uses an Ethernet plug and loose coupler, one in each gripper. The cited UPS uses different connectors and does not specify a two-handed grip.",
        ),
        keypad_code=None,
    ),
    TaskSpec(
        key="clip",
        release_id="DC-clip",
        name="Press the cable into the clip",
        version=1,
        instruction="Press the black network cable into the dark clip on the table, so the cable is held by the clip.",
        setup="Black cord clip stuck to the table; black Ethernet cable laid in a gentle wave passing just in front of the clip, ends routed away from the arms, same path every trial.",
        reset="Pull the cable out of the clip and lay it back along its path in front of the clip.",
        rubric=Rubric(
            guidance="",
            levels=(
                Level(score=1, description="The cable is seated inside the clip."),
                Level(
                    score=0,
                    description="The cable is not inside the clip (for example lying next to it).",
                ),
            ),
        ),
        equipment=(
            Equipment(
                name="Command clear cord clips, 13 clips and 16 strips",
                quantity=1,
                url="https://www.amazon.com/dp/B076ZT3FVN",
                note="Command cord clip, darkened, stuck to the table",
            ),
            Equipment(name="Black Ethernet cable", quantity=1, url=None, note=None),
        ),
        photos=(
            "docs/assets/clip-setup-top.jpg",
            "docs/assets/clip-setup-left.jpg",
            "docs/assets/clip-setup-right.jpg",
        ),
        real_world=RealWorld(
            step="Route cables through a switch tray",
            procedure="Route the cables through the switch tray's routing channel before closing it.",
            quote="Route the cables through the routing channel.",
            source_title="Dell PowerSwitch Tray-21 installation guide",
            source_url="https://www.dell.com/support/manuals/en-ge/networking-s3248t-on/powerswitch_tray-21_install_pub/powerswitch-tray-21-installation-for-the-s5232f-on?guid=guid-41724a60-13ae-4d08-bd3e-35c577d2e2e7&lang=en-us",
            locator=None,
            simplified="We seat one cable in one small clip. The real procedure routes cables through a channel, with different geometry and access constraints.",
        ),
        keypad_code=None,
    ),
)

SPEC_BY_KEY: dict[str, TaskSpec] = {spec.key: spec for spec in SPECS}
"""Every task by its key (the part of the task name after ``datacenterbench/``)."""
