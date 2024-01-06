from pydantic import BaseModel
from pydantic.functional_validators import field_validator
from enum import Enum
import uuid
from typing import Union


class Language(str, Enum):
    ru = 'ru'
    en = 'en'


class ContentType(str, Enum):
    text = 'text'
    photo = 'photo'
    voice = 'voice'
    video_note = 'video_note'


class Reaction(BaseModel):
    name: str = 'std'
    language: Language = Language.ru
    options: list[str] = []


class AdditionText(BaseModel):
    tag: str = uuid.uuid4()
    condition: str
    text: str


class Button(BaseModel):
    text: str
    link: str
    condition: str | None = None


class Var(BaseModel):
    name: str
    value: Union[bool, int, str]
    calculation: str | None = None

    @field_validator('value')
    @classmethod
    def validate_value(cls, value):
        if isinstance(value, str) and value.lower() == 'true':
            return True
        elif isinstance(value, str) and value.lower() == 'false':
            return False
        elif isinstance(value, str) and value.isdigit():
            return int(value)
        else:
            return value


class Message(BaseModel):
    link: str
    start_of_chapter_name: str | None = None
    start_msg: bool = False
    timeout: float = 1.0
    time_typing: float = 4.0
    content_type: ContentType = ContentType.text
    message: str | None = None
    addition_text: list[AdditionText] = []
    media: str | None = None
    next_msg: str | None = None
    buttons: list[Button] = []
    setters: list[Var] = []
    referal_block: int = 0
    level_block: int = 0
    wait_reaction: str = 'std'
    src: str | None = None


class Story(BaseModel):
    language: Language
    messages: list[Message] = []
    reactions: list[Reaction] = [Reaction()]
    start_msg_link: str | None = None


class StoryBunch(BaseModel):
    stories: list[Story] = []


class Result(BaseModel):
    data: bytes
    is_ok: bool
