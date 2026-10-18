"""Example demonstrating the Auto-Tracker service.

This example shows how the Auto-Tracker automatically detects learning events
from AI assistant conversations without manual tracking.
"""

from datetime import datetime, timezone

from learnloop.services.auto_tracker_service import AutoTrackerService, Message


def main():
    """Run Auto-Tracker example."""
    # Initialize the service
    tracker = AutoTrackerService()

    # Simulate a conversation where user learns about async Python
    messages = [
        Message(
            role="user",
            content="How do I implement an async web scraper in Python?",
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="""
            Here's an async web scraper using aiohttp:

            ```python
            import asyncio
            import aiohttp
            from bs4 import BeautifulSoup

            async def fetch_page(session, url):
                async with session.get(url) as response:
                    return await response.text()

            async def scrape_urls(urls):
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for url in urls:
                        task = asyncio.create_task(fetch_page(session, url))
                        tasks.append(task)
                    pages = await asyncio.gather(*tasks)
                    return pages

            # Usage
            urls = ['http://example.com/page1', 'http://example.com/page2']
            results = asyncio.run(scrape_urls(urls))
            ```

            This implementation uses asyncio for concurrent requests. You could alternatively
            use threading with requests, but asyncio is more efficient for I/O-bound tasks.
            Another option would be to use Scrapy framework for more complex scraping needs.
            """,
            timestamp=datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc),
        ),
        Message(
            role="user",
            content="What's the benefit of async over threading here?",
            timestamp=datetime(2024, 1, 1, 10, 2, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="""
            Great question! Here are the key trade-offs:

            1. Memory efficiency - Async uses less memory since it doesn't create OS threads
            2. Scalability - Can handle thousands of concurrent connections easily
            3. Performance - Lower overhead for I/O-bound operations

            However, threading might be better if:
            - You need to integrate with blocking libraries
            - Your code involves CPU-bound work
            - Team is more familiar with threading patterns
            """,
            timestamp=datetime(2024, 1, 1, 10, 3, tzinfo=timezone.utc),
        ),
    ]

    # Analyze the conversation
    project_id = "example-project"
    events = tracker.analyze_conversation(messages, project_id)

    # Display detected learning events
    print(f"\n🎓 Auto-Tracker detected {len(events)} learning events:\n")

    for i, event in enumerate(events, 1):
        print(f"{i}. {event.event_type.value.upper()} Event")
        print(f"   Confidence: {event.confidence:.2f}")
        print(f"   Skills: {', '.join(event.skills)}")
        print(f"   Source: {event.source.value}")

        if event.event_type.value == "implementation":
            print(f"   Language: {event.content['language']}")
            print(f"   Complexity: {event.content['complexity']:.2f}")
            print(f"   Code preview: {event.content['code'][:60]}...")
        elif event.event_type.value == "decision":
            print(f"   Decision: {event.content['decision'][:80]}...")
            print(f"   Alternatives: {len(event.content['alternatives'])}")

        print()

    # Show which events would be auto-stored (confidence > 0.7)
    high_confidence = [e for e in events if e.confidence > 0.7]
    print(f"✓ {len(high_confidence)} events exceed auto-store threshold (0.7)")
    print(f"  These would be automatically tracked without user action.\n")


if __name__ == "__main__":
    main()
