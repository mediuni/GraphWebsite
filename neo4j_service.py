from __future__ import annotations

from typing import Any

import streamlit as st
from neo4j import GraphDatabase, RoutingControl


def _config() -> tuple[str, str, str, str]:
    cfg = st.secrets["neo4j"]
    return (
        cfg["uri"],
        cfg["username"],
        cfg["password"],
        cfg.get("database", "neo4j"),  # หรือชื่อ database ที่คุณตั้งค่าไว้
    )


@st.cache_resource(show_spinner=False)
def get_driver():
    """Create one thread-safe Neo4j Driver for the Streamlit process."""
    uri, username, password, _ = _config()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def query(cypher: str, parameters: dict[str, Any] | None = None, *, write: bool = False) -> list[dict[str, Any]]:
    """Execute parameterized Cypher and return rows as dictionaries."""
    _, _, _, database = _config()
    records, _, _ = get_driver().execute_query(
        cypher,
        parameters_=parameters or {},
        database_=database,
        routing_=RoutingControl.WRITE if write else RoutingControl.READ,
    )
    return [record.data() for record in records]


def ping() -> bool:
    rows = query("RETURN 1 AS ok")
    return bool(rows and rows[0]["ok"] == 1)


def create_schema() -> None:
    statements = [
        "CREATE CONSTRAINT student_id_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.student_id IS UNIQUE",
        "CREATE CONSTRAINT game_genre_id_unique IF NOT EXISTS FOR (g:game_genre) REQUIRE g.game_genre_id IS UNIQUE",
    ]
    for stmt in statements:
        query(stmt, write=True)


def seed_demo_data() -> None:
    """Idempotent sample dataset: safe to run more than once."""
    create_schema()

    students = [
        {"student_id": "S001", "name": "Alice"},
        {"student_id": "S002", "name": "Bob"},
        {"student_id": "S003", "name": "Charlie"},
        {"student_id": "S004", "name": "David"},
        {"student_id": "S005", "name": "Eve"},
        {"student_id": "S006", "name": "Frank"},
        {"student_id": "S007", "name": "Grace"},
        {"student_id": "S008", "name": "Heidi"},
        {"student_id": "S009", "name": "Ivan"},
        {"student_id": "S010", "name": "Judy"}
    ]
    
    game_genres = [
        {"game_genre_id": "G101", "name": "Action"},
        {"game_genre_id": "G102", "name": "RPG"},
        {"game_genre_id": "G103", "name": "FPS"},
        {"game_genre_id": "G104", "name": "MOBA"},
        {"game_genre_id": "G105", "name": "Strategy"},
        {"game_genre_id": "G106", "name": "Simulation"},
        {"game_genre_id": "G107", "name": "Puzzle"},
        {"game_genre_id": "G108", "name": "Racing"},
        {"game_genre_id": "G109", "name": "Sports"},
        {"game_genre_id": "G110", "name": "Horror"}
    ]

    query(
        """
        UNWIND $rows AS row
        MERGE (s:Student {student_id: row.student_id})
        SET s.name = row.name
        """,
        {"rows": students},
        write=True,
    )
    query(
        """
        UNWIND $rows AS row
        MERGE (g:game_genre {game_genre_id: row.game_genre_id})
        SET g.name = row.name
        """,
        {"rows": game_genres},
        write=True,
    )

    friendships = [
        ["S001", "S002"], ["S001", "S005"], ["S001", "S010"],
        ["S002", "S003"], ["S003", "S004"], ["S003", "S008"],
        ["S004", "S005"], ["S004", "S009"], ["S005", "S006"],
        ["S006", "S007"], ["S007", "S008"], ["S008", "S009"],
        ["S009", "S010"], ["S010", "S002"]
    ]
    query(
        """
        UNWIND $rows AS row
        MATCH (a:Student {student_id: row[0]}), (b:Student {student_id: row[1]})
        MERGE (a)-[:FRIEND_OF]->(b)
        """,
        {"rows": friendships},
        write=True,
    )

    genres_likes = [
        {"student_id": "S001", "game_genre_id": "G101", "date": "2018-05-12"},
        {"student_id": "S001", "game_genre_id": "G102", "date": "2020-11-20"},
        {"student_id": "S001", "game_genre_id": "G103", "date": "2022-01-15"},
        {"student_id": "S002", "game_genre_id": "G103", "date": "2015-03-15"},
        {"student_id": "S002", "game_genre_id": "G104", "date": "2017-06-18"},
        {"student_id": "S002", "game_genre_id": "G105", "date": "2019-08-01"},
        {"student_id": "S003", "game_genre_id": "G102", "date": "2017-01-10"},
        {"student_id": "S003", "game_genre_id": "G104", "date": "2021-04-25"},
        {"student_id": "S004", "game_genre_id": "G101", "date": "2014-02-14"},
        {"student_id": "S004", "game_genre_id": "G108", "date": "2016-09-18"},
        {"student_id": "S004", "game_genre_id": "G109", "date": "2018-12-05"},
        {"student_id": "S005", "game_genre_id": "G106", "date": "2019-03-30"},
        {"student_id": "S005", "game_genre_id": "G110", "date": "2022-10-31"},
        {"student_id": "S006", "game_genre_id": "G105", "date": "2013-11-11"},
        {"student_id": "S006", "game_genre_id": "G107", "date": "2016-07-20"},
        {"student_id": "S007", "game_genre_id": "G102", "date": "2018-04-05"},
        {"student_id": "S007", "game_genre_id": "G104", "date": "2020-08-14"},
        {"student_id": "S007", "game_genre_id": "G106", "date": "2023-02-28"},
        {"student_id": "S008", "game_genre_id": "G103", "date": "2016-10-10"},
        {"student_id": "S008", "game_genre_id": "G108", "date": "2019-05-22"},
        {"student_id": "S009", "game_genre_id": "G101", "date": "2015-08-08"},
        {"student_id": "S009", "game_genre_id": "G107", "date": "2018-12-12"},
        {"student_id": "S009", "game_genre_id": "G110", "date": "2021-09-01"},
        {"student_id": "S010", "game_genre_id": "G105", "date": "2017-04-01"},
        {"student_id": "S010", "game_genre_id": "G109", "date": "2020-10-15"}
    ]
    query(
        """
        UNWIND $rows AS row
        MATCH (s:Student {student_id: row.student_id}), (g:game_genre {game_genre_id: row.game_genre_id})
        MERGE (s)-[r:GENRES_LIKES]->(g)
        SET r.genres_like_date = date(row.date)
        """,
        {"rows": genres_likes},
        write=True,
    )


def get_students() -> list[dict[str, Any]]:
    return query("MATCH (s:Student) RETURN s.student_id AS student_id, s.name AS name ORDER BY s.student_id")


def find_student(student_id: str) -> dict[str, Any] | None:
    result = query(
        """
        MATCH (s:Student {student_id:$student_id})
        RETURN s.student_id AS id, s.name AS name
        """,
        {"student_id": student_id}
    )
    return result[0] if result else None


def get_dashboard_metrics() -> dict[str, int]:
    rows = query(
        """
        MATCH (s:Student) WITH count(s) AS students
        MATCH (g:game_genre) WITH students, count(g) AS game_genres
        MATCH ()-[r:GENRES_LIKES]->() WITH students, game_genres, count(r) AS likes
        MATCH ()-[f:FRIEND_OF]->()
        RETURN students, game_genres, likes, count(f) AS friendships
        """
    )
    return rows[0] if rows else {"students": 0, "game_genres": 0, "likes": 0, "friendships": 0}


def game_genres_likes(student_id: str) -> list[dict[str, Any]]:
    return query(
        """
        MATCH
            (s:Student {student_id:$student_id})
            -[r:GENRES_LIKES]->
            (g:game_genre)
        RETURN
            g.game_genre_id AS game_genre_id,
            g.name AS name,
            r.genres_like_date AS genres_like_date
        ORDER BY genres_like_date
        """,
        {"student_id": student_id}
    )


def recommend_game_genres(student_id: str) -> list[dict[str, Any]]:
    """Recommend game genres based on friends' likes."""
    return query(
        """
        MATCH
            (me:Student {student_id:$student_id})
            -[:FRIEND_OF]-
            (friend:Student)
            -[:GENRES_LIKES]->
            (genre:game_genre)
        WHERE NOT EXISTS {
            MATCH (me)-[:GENRES_LIKES]->(genre)
        }
        RETURN
            genre.game_genre_id AS game_genre_id,
            genre.name AS recommendation,
            count(DISTINCT friend) AS score
        ORDER BY
            score DESC,
            recommendation
        """,
        {"student_id": student_id},
    )


def list_game_genres() -> list[str]:
    return [row["name"] for row in query("MATCH (g:game_genre) RETURN g.name AS name ORDER BY g.name")]


def graph_neighborhood(student_id: str, limit: int = 40) -> list[dict[str, Any]]:
    return query(
        """
        MATCH (u:Student {student_id:$student_id})
        OPTIONAL MATCH p=(u)-[:FRIEND_OF|GENRES_LIKES*1..2]-(x)
        WITH u, collect(p)[0..$limit] AS paths
        UNWIND paths AS p
        UNWIND relationships(p) AS r
        WITH DISTINCT startNode(r) AS s, r, endNode(r) AS t
        RETURN elementId(s) AS source_id, labels(s)[0] AS source_label,
               coalesce(s.name, s.student_id, s.game_genre_id) AS source_name,
               type(r) AS relationship,
               elementId(t) AS target_id, labels(t)[0] AS target_label,
               coalesce(t.name, t.student_id, t.game_genre_id) AS target_name
        LIMIT $limit
        """,
        {"student_id": student_id, "limit": int(limit)},
    )