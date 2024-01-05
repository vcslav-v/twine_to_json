from bs4 import BeautifulSoup
from twine_to_json import schemas, MAX_BUTTON_LEN
from twine_to_json import logger
import regex as re
import json
import zipfile


def prepare_condition(condition: str, message_link: str, title: str):
    condition = re.sub(r'\$(\w+)', r'{\1}', condition.strip())
    condition = condition.replace('is not', '!=')
    condition = condition.replace(' is ',  ' == ')
    condition = condition.replace('false', '0')
    condition = condition.replace('true', '1')
    if re.sub(r'{\w+}|==| |\d|<|>|and|or|!=|\+|-|\/|\*', '', condition):
        logger.error(f'Condition is not correct - {message_link} - {title} - {condition}')
    return condition


def add_message_text(message: schemas.Message, text: str) -> schemas.Message:
    condition_parts = re.findall(r'(\(if:(.*?)\)\[(.*?)\])', text)
    for condition_part in condition_parts:
        expression, condition, ad_text = condition_part
        addition_text = schemas.AdditionText(
            text=ad_text,
            condition=prepare_condition(condition, message.link, message.src),
        )
        text = text.replace(expression, '{'+addition_text.tag+'}')
        message.addition_text.append(addition_text)
    message.message = text
    return message


def add_message_settings(msg_vars: list(set[str]), message: schemas.Message, row_text: str) -> schemas.Message:
    for p_var in msg_vars:
        field, value = p_var[1], p_var[3]
        if field.strip('"\'\\/')[0] == '$':
            msg_var = schemas.Var(
                name=field.strip('"\'\\/ ')[1:],
                value=value.strip('"\'\\/ '),
            )
            if isinstance(msg_var.value, bool):
                setter = schemas.Var(
                    name=msg_var.name,
                    value=1 if msg_var.value else 0,
                )
            elif isinstance(msg_var.value, int):
                setter = schemas.Var(
                    name=msg_var.name,
                    value=msg_var.value,
                )
            elif isinstance(msg_var.value, str):
                setter = schemas.Var(
                    name=msg_var.name,
                    calculation=prepare_condition(msg_var.value, message.link, message.src),
                )
            message.setters.append(setter)
        else:
            if field == '_media':
                iter_data = zip(
                    re.findall(r'\"(.*?)\"', re.findall(r'(\(dm:)(.*)(\))', value)[0][1])[::2],
                    re.findall(r'\"(.*?)\"', re.findall(r'(\(dm:)(.*)(\))', value)[0][1])[1::2]
                )
                m_data = {}
                for m_key, m_value in iter_data:
                    _value = m_value.strip('"\'\\/ ')
                    m_data[m_key.strip('"')] = int(_value) if _value.isdigit() else _value

                try:
                    message.content_type = schemas.ContentType(m_data['media_type'])
                except ValueError:
                    logger.error(
                        f'Content type is not correct - {message.link} - {message.src} - {m_data["media_type"]}'
                    )

                message.media = m_data['file']

                if m_data.get('caption'):
                    message.message = m_data.get('caption')
            elif field == '_start_chapter':
                _value = value.strip('"\'\\/')
                message.start_of_chapter_name = _value
            elif field == '_push_next' and value.strip('"\'\\/') == 'true':
                push_link = re.search(r'(\[\[)([^|]*?)(\]\])', row_text)
                if push_link:
                    message.next_msg = push_link.group(2)
            elif field == '_referal_block':
                _value = int(value.strip('"\'\\/'))
                message.referal_block = _value
            elif field == '_level_block':
                _value = int(value.strip('"\'\\/'))
                message.level_block = _value
            elif field == '_wait_reaction':
                _value = value.strip('"\'\\/')
                message.wait_reaction = _value
            elif field == '_timeout':
                _value = float(value.strip('"\'\\/'))
                message.timeout = _value
            elif field == '_time_typing':
                _value = float(value.strip('"\'\\/'))
                message.time_typing = _value

    return message


def add_buttons(passage_text: str, message: schemas.Message) -> schemas.Message:
    for button_data in re.findall(
        r'(\(if:(.*?)\)\s*?)?(\[\[)(.*?)(\]\])',
        passage_text
    ):
        raw_button = button_data[3]
        button_text, *button_link = raw_button.split('|')
        if len(button_link) > 1:
            logger.error(f'Button link is not correct - {message.link} - {message.src} - {raw_button}')
            continue
        if button_link:
            button_link = button_link[0]
        else:
            button_link = button_text

        if len(button_text) > MAX_BUTTON_LEN:
            logger.error(f'Button text more than {MAX_BUTTON_LEN} - {message.link} - {message.src} - {raw_button}')
        message.buttons.append(
            schemas.Button(
                text=button_text,
                link=button_link,
            )
        )
        if button_data[1]:
            message.buttons[-1].condition = prepare_condition(button_data[1], message.link, message.src)
    return message


def parse_chapter(chapter_path: str, story: schemas.Story, zip_data: zipfile.ZipFile) -> schemas.Story:
    with zip_data.open(chapter_path) as f:
        soup = BeautifulSoup(f, 'lxml')
    title = soup.title.text
    passagedatas = soup.body.find('tw-storydata').find_all('tw-passagedata')

    start_node_pid = soup.body.find('tw-storydata').attrs['startnode']
    start_node_link = soup.body.find('tw-storydata').find(
        'tw-passagedata',
        attrs={'pid': start_node_pid}
    ).attrs['name']

    for passagedata in passagedatas:
        message = schemas.Message(link=passagedata['name'], src=title)
        if len(passagedata.attrs['name']) > MAX_BUTTON_LEN:
            logger.error(f'Button name is too long - {passagedata.attrs["name"]} - {message.link} - {title}')

        message.content_type = schemas.ContentType.text

        text = re.sub(
            r'(\(set:.*?\(dm:.*?\)\))|(\(set:.*?\)|(\[\[.*?\]\]))|\(if:.*?\)\s*?\[\[.*?\]\]',
            '',
            passagedata.text
        ).strip()

        if text:
            try:
                message = add_message_text(message, text)
            except Exception as e:
                logger.error(f'Error while parsing message text - {message.link} - {title} - {e}')

        passage_vars = re.findall(r'(\(set: )(.*?)( to )(.*)(\))', passagedata.text)

        try:
            message = add_message_settings(passage_vars, message, passagedata.text)
        except Exception as e:
            logger.error(f'Error while parsing message settings - {message.link} - {title} - {e}')

        if not message.next_msg:
            try:
                message = add_buttons(passagedata.text, message)
            except Exception as e:
                logger.error(f'Error while parsing message buttons - {message.link} - {title} - {e}')
        if not story.start_msg_link and message.link == start_node_link:
            message.start_msg = True
            story.start_msg_link = message.link
        story.messages.append(message)

    return story


def add_reaction(reaction_path: str, story: schemas.Story, zip_data: zipfile.ZipFile) -> schemas.Story:
    with zip_data.open(reaction_path) as f:
        reactions_data = json.load(f)
        if 'std' not in reactions_data.keys():
            logger.error(f'Reaction file must contain "std" reaction - {reaction_path}')
        for name, options in reactions_data.items():
            story.reactions.append(
                schemas.Reaction(
                    name=name,
                    language=story.language,
                    options=options,
                )
            )

    return story


def parse_twine(lang: str, zip_data: zipfile.ZipFile, chapters: list[str] = [], reactions: str = '') -> schemas.Story:
    if hasattr(schemas.Language, lang):
        story = schemas.Story(language=schemas.Language(lang))
    else:
        logger.error(f'Language "{lang}" is not supported')
        story = schemas.Story(language=schemas.Language.ru)
    for chapter in chapters:
        story = parse_chapter(chapter, story, zip_data)

    if reactions:
        try:
            story = add_reaction(reactions, story, zip_data)
        except Exception as e:
            logger.error(f'Error while parsing reactions for {lang} version - {e}')

    return story
