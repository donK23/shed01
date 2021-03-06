"""
Models
"""

import numpy as np
import pandas as pd
from sqlalchemy import sql, create_engine, MetaData, Table, Column, Integer, VARCHAR, TIMESTAMP
from sklearn.metrics import jaccard_similarity_score


class DB:
    def __init__(self):
        from instance.config import PG_USER, PG_PASSWORD
        # connection
        db_uri = "postgresql://" + PG_USER + ":" + PG_PASSWORD + "@localhost/shrecdb"
        engine = create_engine(db_uri)
        self.connection = engine.connect()
        # schema
        metadata = MetaData()
        self.books_schema = Table("books", metadata, Column("book_id", Integer, nullable=False, primary_key=True),
                                  Column("title", VARCHAR))
        self.ratings_schema = Table("ratings", metadata, Column("user_id", Integer, nullable=False, primary_key=True),
                                    Column("rated_at", TIMESTAMP), Column("rat_book_01", Integer),
                                    Column("rat_book_02", Integer), Column("rat_book_03", Integer),
                                    Column("rat_book_04", Integer), Column("rat_book_05", Integer),
                                    Column("rat_book_06", Integer), Column("rat_book_07", Integer),
                                    Column("rat_book_08", Integer), Column("rat_book_09", Integer),
                                    Column("rat_book_10", Integer), Column("rat_book_11", Integer),
                                    Column("rat_book_12", Integer), Column("rat_book_13", Integer),
                                    Column("rat_book_14", Integer), Column("rat_book_15", Integer),)

    def get_books(self):
        """
        Get books data from DB
        :return: Pandas Dataframe {book_id, title}
        """
        # DB query
        query_books = "SELECT * FROM books"
        books = self.connection.execute(sql.text(query_books))
        self.connection.close()

        # Data processing
        book_ids = []; titles = []
        for book in books:
            book_ids.append(book[0])
            titles.append(book[1])

        # Dataframe
        books = {"BOOK_ID": book_ids, "TITLE": titles}

        return pd.DataFrame(books)

    def get_ratings(self):
        """
        Get ratings data from DB
        :return: Pandas Dataframe {user_id, rated_at, ratings_per_book[1:15}
        """
        # DB query
        query_ratings = "SELECT * FROM ratings"
        all_ratings = self.connection.execute(sql.text(query_ratings))
        self.connection.close()

        # Data processing
        user_ids = []; ts = []; br01 = []; br02 = []; br03 = []; br04 = []; br05 = []; br06 = []; br07 = []; br08 = [];
        br09 = []; br10 = []; br11 = []; br12 = []; br13 = []; br14 = []; br15 = []
        for rating in all_ratings:
            user_ids.append(rating[0])
            ts.append(rating[1])
            br01.append(rating[2]); br02.append(rating[3]); br03.append(rating[4]); br04.append(rating[5]);
            br05.append(rating[6]); br06.append(rating[7]); br07.append(rating[8]);br08.append(rating[9]);
            br09.append(rating[10]); br10.append(rating[11]); br11.append(rating[12]); br12.append(rating[13]);
            br13.append(rating[14]); br14.append(rating[15]); br15.append(rating[16])

        # Dataframe
        ratings = {"USER_ID": user_ids, "RATED_AT": ts, "RAT_B01": br01, "RAT_B02": br02, "RAT_B03": br03,
                   "RAT_B04": br04, "RAT_B05": br05, "RAT_B06": br06, "RAT_B07": br07, "RAT_B08": br08, "RAT_B09": br09,
                   "RAT_B10": br10, "RAT_B11": br11, "RAT_B12": br12, "RAT_B13": br13, "RAT_B14": br14, "RAT_B15": br15}
        return pd.DataFrame(ratings)

    def insert_user_rating(self, user_rating):
        """
        Insert new rating from user into DB
        :param user_rating: list of ratings, sorted from book01 to book15
        :return: confirmation string
        """
        insert = self.ratings_schema.insert().values(rat_book_01 = user_rating[0], rat_book_02 = user_rating[1],
                                                     rat_book_03 = user_rating[2], rat_book_04 = user_rating[3],
                                                     rat_book_05 = user_rating[4], rat_book_06 = user_rating[5],
                                                     rat_book_07 = user_rating[6], rat_book_08 = user_rating[7],
                                                     rat_book_09 = user_rating[8], rat_book_10 = user_rating[9],
                                                     rat_book_11 = user_rating[10], rat_book_12 = user_rating[11],
                                                     rat_book_13 = user_rating[12], rat_book_14 = user_rating[13],
                                                     rat_book_15 = user_rating[14])
        self.connection.execute(insert)
        self.connection.close()
        return "Rating inserted: " + str(user_rating)


class RecommendationEngine:
    def __init__(self, user_rating, collaborative_data):
        self.user_rating = user_rating
        self.collaborative_data = collaborative_data

    def recommend_books(self):
        """
        Recommend books wtih user input based on collaborative dataset
        :return: sorted list of recommended books tuples (book_id, recommendation_score)
        """

        def all_books_recommendation(user_rating=self.user_rating, ratings_data=self.collaborative_data,
                                     method=jaccard_similarity_score):
            """
            Recommendation engine based on collaborative filtering. Creates recommendation array summing up weighted similarity
            scores by book, divided by sum of user similarities per rating.

            :param user_rating: list of user inputs as int. Size 15, nan replaced with 0
            :param ratings_data: dataframe with user ratings for the 15 books
            :param method: similarity measurement method. Jaccard similarity (default)
            :return: array of recommendation ratings for all 15 books
            """
            ratings_matrix = ratings_data.ix[: , "RAT_B01":"RAT_B15"].as_matrix().astype(float)
            weighted_ratings = np.array([]); user_similarities = np.array([])
            for row in ratings_matrix:
                similarity_coefficient = method(user_rating, row)
                weighted_row = row * similarity_coefficient
                row[row != 0.] = similarity_coefficient
                if weighted_ratings.size == 0 and user_similarities.size == 0:
                    weighted_ratings = np.hstack((weighted_ratings, weighted_row))
                    user_similarities = np.hstack((user_similarities, row))
                else:
                    weighted_ratings = np.vstack((weighted_ratings, weighted_row))
                    user_similarities = np.vstack((user_similarities, row))
            total = np.sum(weighted_ratings, axis=0)
            sim_sum = np.sum(user_similarities, axis=0)
            return total / sim_sum

        def filter_recommendation(recommendation, user_input=self.user_rating):
            """
            Filter recommendation array based on input books

            :param recommendation: recommendation array of unsorted recommendation values
            :param user_input: list from user input
            :return: tuple ([index of recommended books],[ratings of recommended books])
            """
            recommend_books = []
            recommend_books_ratings = []
            for position, item in enumerate(user_input):
                if item == 0:
                    recommend_books.append(position)
            for book_id in  recommend_books:
                recommend_books_ratings.append(recommendation[book_id])
            return recommend_books, recommend_books_ratings

        def sort_recommendation(recommended_idx, recommended_ratings):
            """
            Sort recommendation based on rating values

            :param recommended_idx: list of book indices from recommendation
            :param recommended_ratings: list of ratings from recommendation
            :return: list of sorted recommendations - tuple of (book_id, rating)
            """
            recommended_dict = {}
            for id, rating in zip(recommended_idx, recommended_ratings):
                recommended_dict[id] = rating
            return sorted(recommended_dict.items(), key=lambda x: x[1], reverse=True)

        recommended_books, recommended_ratings = filter_recommendation(all_books_recommendation(self.user_rating))
        recommendation_for_user = sort_recommendation(recommended_books, recommended_ratings)
        return recommendation_for_user

