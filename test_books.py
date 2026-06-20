import pytest
from conftest import client, setup_database
import time

def test_get_books_empty(setup_database):
    """Test getting books when database is empty"""
    response = client.get("/books?skip=0&limit=10")
    assert response.status_code == 200
    assert response.json() == []  # Empty list


def test_create_author_and_book(setup_database):
    """Test creating an author and a book"""
    # Step 1: Create an author
    author_response = client.post("/create-author", json={
        "name": "J.R.R. Tolkien",
        "email": "tolkien@example.com",
        "password": "secret123"
    })
    assert author_response.status_code == 201
    assert author_response.json()["name"] == "J.R.R. Tolkien"
    
    # Step 2: Create a book
    book_response = client.post("/create-book", json={
        "book_name": "The Hobbit",
        "author_name": "J.R.R. Tolkien",
        "pages": 310
    })
    assert book_response.status_code == 201
    assert book_response.json()["book_name"] == "The Hobbit"


def test_get_book_by_id(setup_database):
    """Test getting a specific book by ID"""
    # First create an author and book
    client.post("/create-author", json={
        "name": "George Orwell",
        "email": "orwell@example.com",
        "password": "secret123"
    })
    book_response = client.post("/create-book", json={
        "book_name": "1984",
        "author_name": "George Orwell",
        "pages": 328
    })
    book_id = book_response.json()["id"]
    
    # Now get the book by ID
    response = client.get(f"/book/{book_id}")
    assert response.status_code == 200
    assert response.json()["book_name"] == "1984"


def test_get_nonexistent_book(setup_database):
    """Test getting a book that doesn't exist"""
    response = client.get("/book/9999")
    assert response.status_code == 404


def test_update_book(setup_database):
    """Test updating a book"""
    # Create author and book
    client.post("/create-author", json={
        "name": "J.K. Rowling",
        "email": "rowling@example.com",
        "password": "secret123"
    })
    book_response = client.post("/create-book", json={
        "book_name": "Harry Potter",
        "author_name": "J.K. Rowling",
        "pages": 300
    })
    book_id = book_response.json()["id"]
    
    # Update the book
    response = client.put(f"/update-book/{book_id}", json={
        "pages": 350
    })
    assert response.status_code == 200
    assert response.json()["pages"] == 350


def test_delete_book(setup_database):
    """Test deleting a book"""
    # Create author and book
    client.post("/create-author", json={
        "name": "Stephen King",
        "email": "king@example.com",
        "password": "secret123"
    })
    book_response = client.post("/create-book", json={
        "book_name": "The Shining",
        "author_name": "Stephen King",
        "pages": 447
    })
    book_id = book_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/delete-book/{book_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/book/{book_id}")
    assert get_response.status_code == 404