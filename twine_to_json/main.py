from twine_to_json import twine_parser, schemas
from twine_to_json.config import logger, log_stream
import os
import io
import zipfile


def get_story_file_names(zip_data: zipfile.ZipFile) -> dict:
    story_file_names = {}
    # Collect html twine files
    for file_name in zip_data.namelist():
        if file_name.endswith('.html'):
            story_file_name_raw = file_name.split('-')
            if len(story_file_name_raw) < 3:
                logger.error(f'File name is not correct {file_name}')
                continue
            chapter_number = story_file_name_raw[-2]
            if not chapter_number.isdigit():
                logger.error(f'Chapter number is not digit {file_name}')
                continue
            language = story_file_name_raw[-1].split('.')[0]
            story_file_names.setdefault(language, {})
            story_file_names[language].setdefault('chapters', [])
            story_file_names[language]['chapters'].append(
                (int(chapter_number), file_name)
            )

    # Collect json reactions files
    for file_name in zip_data.namelist():
        if file_name.endswith('.json'):
            reaction_file_name_raw = file_name.split('-')
            if len(reaction_file_name_raw) < 2:
                logger.error(f'File name is not correct {file_name}')
                continue
            language = reaction_file_name_raw[-1].split('.')[0]
            if language not in story_file_names:
                logger.error(f'There is no story in {language} for reaction file - {file_name}')
                continue
            story_file_names[language].setdefault('reactions', file_name)

    for language in story_file_names:
        if 'reactions' not in story_file_names[language]:
            logger.error(f'There is no reaction file for {language}')
            continue

    for language in story_file_names:
        story_file_names[language]['chapters'].sort(key=lambda x: x[0])
        story_file_names[language]['chapters'] = [x[1] for x in story_file_names[language]['chapters']]
    return story_file_names


def check_story_connection(story: schemas.Story):
    checked_links = []
    all_links = [message.link for message in story.messages]

    start_msg_link = story.start_msg_link
    all_chapters_links = [
        message.link for message in story.messages if message.start_of_chapter_name and message.link != start_msg_link
    ]

    for message in story.messages:
        if message.link in checked_links:
            logger.error(f'Duplicate name - {message.link} - {message.src}')
        checked_links.append(message.link)

        if message.next_msg:
            if message.next_msg in all_chapters_links:
                all_chapters_links.remove(message.next_msg)
            if message.next_msg not in all_links:
                logger.error(f'Next message link not found - {message.link} - {message.src}')

        for button in message.buttons:
            if button.link in all_chapters_links:
                all_chapters_links.remove(button.link)
            if button.link not in all_links:
                logger.error(f'Button link not found - {message.link} - {message.src}')

    if all_chapters_links:
        logger.error(f'Chapter link not found - {all_chapters_links} - {story.language}')


def check_media(story: schemas.Story) -> set[str]:
    all_media = set()
    for message in story.messages:
        if message.content_type == schemas.ContentType.text and message.media:
            logger.error(f'Text message with media - {message.link} - {message.src}')
        elif message.content_type == schemas.ContentType.text and not message.message:
            logger.error(f'Text message without text - {message.link} - {message.src}')
        elif message.content_type != schemas.ContentType.text and not message.media:
            logger.error(f'Media message without media - {message.link} - {message.src}')

        if message.content_type == schemas.ContentType.photo:
            if not message.media.endswith(('.jpg', '.jpeg', '.png')):
                logger.error(f'Photo message with wrong media - {message.link} - {message.src}')
                continue
            all_media.add(message.media)
        elif message.content_type == schemas.ContentType.voice:
            if not message.media.endswith(('.ogg')):
                logger.error(f'Voice message with wrong media - {message.link} - {message.src}')
                continue
            all_media.add(message.media)
        elif message.content_type == schemas.ContentType.video_note:
            if not message.media.endswith(('.mp4')):
                logger.error(f'Video note message with wrong media - {message.link} - {message.src}')
                continue
            all_media.add(message.media)
    return all_media


def get_media_mock(media: str) -> str:
    if media.endswith(('.jpg', '.jpeg', '.png')):
        return 'test.jpeg'
    elif media.endswith(('.ogg')):
        return 'test.ogg'
    elif media.endswith(('.mp4')):
        return 'test.mp4'
    else:
        return 'unknown'


def check_lang_versions(story_bunch: schemas.StoryBunch):
    for i_story in story_bunch.stories:
        i_links = set([message.link for message in i_story.messages])
        for j_story in story_bunch.stories:
            if i_story.language == j_story.language:
                continue
            j_links = set([message.link for message in j_story.messages])
            links_diff = i_links.difference(j_links)
            for d_link in links_diff:
                i_msg = [message for message in i_story.messages if message.link == d_link][0]
                logger.error(f'Link {d_link} from {i_story.language} - {i_msg.src} is not found in {j_story.language} story')


def convert(data: io.BytesIO) -> schemas.Result:
    zip_data = zipfile.ZipFile(data)
    story_files_data = get_story_file_names(zip_data)
    story_bunch = schemas.StoryBunch()
    for lang, file_pack in story_files_data.items():
        logger.info(f'Parsing {lang} story pack')
        story_bunch.stories.append(twine_parser.parse_twine(lang, zip_data, **file_pack))
    all_media = set()
    check_lang_versions(story_bunch)
    for story in story_bunch.stories:
        check_story_connection(story)
        all_media = all_media.union(check_media(story))

    if log_stream.getvalue():
        log_stream.seek(0)
        return schemas.Result(data=log_stream.getvalue(), is_ok=False)

    zip_buffer = io.BytesIO()
    directory = os.path.dirname(__file__)
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for media in all_media:
            zf.write(os.path.join(directory, get_media_mock(media)), os.path.join('media', media))
        zf.writestr('story.json', story_bunch.model_dump_json())
    zip_buffer.seek(0)
    return schemas.Result(data=zip_buffer.getvalue(), is_ok=True)


if __name__ == '__main__':
    with open('test.zip', 'rb') as f:
        convert(f)