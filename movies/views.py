import difflib
import pandas as pd

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Movie
from users.forms import UserRegisterForm
from users.models import Watchlist
from users.models import Review


values = ('imdb_id', 'title', 'rating_id__rating', 'link', 'votes', 'genres_id__genres', 'cast', 'runtime_id__runtime',
          'mtype_id__mtype', 'netflix_id__netflix', 'plot', 'keywords', 'release', 'year_id__year', 'poster',
          'youtube_id__youtube')

all_movies = Movie.objects.values_list(*values)


def get_watchlist(request):
    if request.user.is_authenticated:
        return list([x.movie for x in Watchlist.objects.filter(author=request.user)])
    else: return False


def register(request):
    if request.user.is_authenticated:
        return redirect('main-page')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()

            new_user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'], )
            login(request, new_user)

            messages.success(request, f'Thanks for registering. You are now logged in.')
            return redirect('main-page')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def watchlist(request):
    my_watchlist = get_watchlist(request)

    if request.method == 'POST':
        movie = request.POST.get('movie')
        if movie[:6] != "delete":
            if movie not in my_watchlist:
                add_movie = Watchlist(movie=movie, author=request.user)
                messages.success(request, f'{movie} successfully added to your watchlist!')
                add_movie.save()
                return redirect(request.META['HTTP_REFERER'])
            else:
                messages.info(request, f'{movie} was already in your watchlist!')
                return redirect(request.META['HTTP_REFERER'])
        else:
            delete_movie = Watchlist.objects.filter(movie=movie[6:], author=request.user)
            messages.error(request, f'{movie[6:]} has been deleted from your watchlist!')
            delete_movie.delete()
            return redirect(request.META['HTTP_REFERER'])

    user_watchlist = [all_movies.get(title=val) for val in my_watchlist]

    print(user_watchlist)

    page = request.GET.get('page', 1)
    paginator_watchlist = Paginator(user_watchlist, 15)

    try:
        user_watchlist = paginator_watchlist.page(page)
    except PageNotAnInteger:
        user_watchlist = paginator_watchlist.page(1)
    except EmptyPage:
        user_watchlist = paginator_watchlist.page(paginator_watchlist.num_pages)

    return render(request, 'watchlist.html', {'userWatchlist': user_watchlist, 'myWatchlist': my_watchlist})


def main_page(request):
    return render(request, 'main-page.html')


# def all_movies(request):
#     return render(request, 'all.html', {'dfList': dfList})


def all_series(request):
    my_watchlist = get_watchlist(request)
    series_list = list(all_movies.filter(mtype_id__mtype='Series'))

    page = request.GET.get('page', 1)
    paginator_all_series = Paginator(series_list, 15)

    try:
        movie_items = paginator_all_series.page(page)
    except PageNotAnInteger:
        movie_items = paginator_all_series.page(1)
    except EmptyPage:
        movie_items = paginator_all_series.page(paginator_all_series.num_pages)

    return render(request, 'special-item.html', {'movieItems': movie_items, 'myWatchlist': my_watchlist})


def netflix(request):
    my_watchlist = get_watchlist(request)
    netflix_movies = list(all_movies.exclude(netflix_id__netflix='None').order_by('-release'))

    page = request.GET.get('page', 1)
    paginator_netflix = Paginator(netflix_movies, 15)

    try:
        movie_items = paginator_netflix.page(page)
    except PageNotAnInteger:
        movie_items = paginator_netflix.page(1)
    except EmptyPage:
        movie_items = paginator_netflix.page(paginator_netflix.num_pages)

    return render(request, "special-item.html", {'movieItems': movie_items, 'myWatchlist': my_watchlist})


def top_movies(request):
    my_watchlist = get_watchlist(request)

    top_list = list(all_movies.order_by('-rating_id__rating')[:100])
    page = request.GET.get('page', 1)
    paginator_top_movies = Paginator(top_list, 15)

    try:
        movie_items = paginator_top_movies.page(page)
    except PageNotAnInteger:
        movie_items = paginator_top_movies.page(1)
    except EmptyPage:
        movie_items = paginator_top_movies.page(paginator_top_movies.num_pages)

    return render(request, 'special-item.html', {'movieItems': movie_items, 'myWatchlist': my_watchlist})


def advanced_search(request):
    cast = pd.read_csv('movies.csv')['cast']
    all_cast = list(set([j for sub in list(cast.str[2:-2].str.replace("'", "").str.replace('"', '')
                                           .str.split(', ')) for j in sub]))

    my_watchlist = get_watchlist(request)

    global paginator_advanced_search
    page = request.GET.get('page', 1)

    if request.method == 'GET' and (request.GET.get('getYear') is not None or request.GET.get('getRate') is not None) \
            and request.GET.get('page') is None:
        get_rating = request.GET.get('getRate')
        get_year = request.GET.get('getYear')
        get_cast = request.GET.get('getCast')
        get_keywords = request.GET.get('getKeywords')
        get_genre = request.GET.get('getGenre')
        sorting = request.GET.get('sorting')

        if get_cast:
            get_cast = difflib.get_close_matches(get_cast, all_cast)

            if len(get_cast) > 0:
                get_cast = get_cast[0]
            else:
                get_cast = 'No matches'
        else:
            get_cast = ''

        if get_genre == 'All': get_genre = ''
        if not get_year: get_year = 0
        if not get_rating: get_rating = 0.0

        rating = all_movies.filter(rating_id__rating__gte=float(get_rating))
        year = all_movies.filter(year_id__year__gte=float(get_year))
        genres = all_movies.filter(genres_id__genres__icontains=get_genre)
        cast = all_movies.filter(cast__icontains=get_cast)
        keywords = all_movies.filter(keywords__icontains=get_keywords)

        if sorting == 'byYear':
            select = list(all_movies.intersection(year).order_by('-release'))
        elif sorting == 'byVotes':
            select = list(all_movies.intersection(rating, year, genres, cast, keywords).order_by('-votes'))
        else:
            select = list(all_movies.intersection(rating, year, genres, cast, keywords).order_by('-rating_id__rating'))

        if get_genre == '': get_genre = 'All'
        if get_cast == '': get_cast = 'All'
        if get_keywords == '': get_keywords = 'Any'

        if sorting == 'byYear':
            sorting = 'By Year'
        elif sorting == 'byVotes':
            sorting = 'By Votes'
        else:
            sorting = 'By Rating'

        paginator_advanced_search = Paginator(select, 15)

        try:
            movie_items = paginator_advanced_search.page(page)
        except PageNotAnInteger:
            movie_items = paginator_advanced_search.page(1)
        except EmptyPage:
            movie_items = paginator_advanced_search.page(paginator_advanced_search.num_pages)

        return render(request, 'advanced_search.html', {'getRate': get_rating, 'getYear': get_year,
                                                        'getGenre': get_genre, 'getCast': get_cast,
                                                        'getKeywords': get_keywords, 'sorting': sorting,
                                                        'movieItems': movie_items, 'myWatchlist': my_watchlist})
    elif request.method == 'GET' and \
            (request.GET.get('getYear') is None or request.GET.get('getRate') is None) and \
            request.GET.get('page') is not None:
        try:
            movie_items = paginator_advanced_search.page(page)
        except EmptyPage:
            movie_items = paginator_advanced_search.page(paginator_advanced_search.num_pages)

        return render(request, 'advanced_search.html', {'movieItems': movie_items, 'myWatchlist': my_watchlist})
    else:
        return render(request, 'advanced_search.html')


def genre(request):
    my_watchlist = get_watchlist(request)

    global paginator_genre
    page = request.GET.get('page', 1)

    if request.method == 'GET' and request.GET.get('typeGenre') is not None and request.GET.get('page') is None:
        genre_type = request.GET.get('typeGenre', 'False')

        top_genre = list(all_movies.filter(genres_id__genres__contains=genre_type).order_by('-rating_id__rating'))

        paginator_genre = Paginator(top_genre, 15)

        try:
            movie_items = paginator_genre.page(page)
        except PageNotAnInteger:
            movie_items = paginator_genre.page(1)
        except EmptyPage:
            movie_items = paginator_genre.page(paginator_genre.num_pages)

        return render(request, 'special-item.html', {'movieItems': movie_items, 'genreType': genre_type,
                                                     'myWatchlist': my_watchlist})
    elif request.method == 'GET' and request.GET.get('typeGenre') is None and request.GET.get('page') is not None:
        try:
            movie_items = paginator_genre.page(page)
        except EmptyPage:
            movie_items = paginator_genre.page(paginator_genre.num_pages)

        return render(request, 'special-item.html', {'movieItems': movie_items, 'myWatchlist': my_watchlist})
    else:
        return render(request, 'special-item.html')


def show_intro(request):
    youtube = request.POST.get('intro', 'False')
    title = request.POST.get('title', 'False')

    if youtube != 'False' and title != 'False':
        imdb = all_movies.get(title=title)[0]
        return render(request, "intro.html", {'youtube': "https://www.youtube.com/watch?v=" + youtube, 'title': title,
                                              'imdb': imdb})
    else:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def result_page(request, movie_id: str):
    movie = request.POST.get('movie', False)
    intro = request.POST.get('intro', False)
    msg = request.POST.get('msg', False)
    if movie or movie_id:
        search = list(all_movies.get(imdb_id=movie_id))

        imdb_id = search[0].strip()
        title = search[1].strip()
        rating = int(float(str(search[2]).strip()) * 10)
        link = search[3].strip()
        votes = search[4]
        genres = search[5].strip()
        genres_split = genres.split(',')
        cast = search[6].strip()
        cast_list = cast[2:-2].replace("'", "").split(',')
        runtime = search[7]
        mType = search[8].strip()
        netflix = search[9].strip()
        plot = search[10].strip()
        year = search[13]
        poster = search[14].strip()
        if intro == 'noIntro':
            youtube = 'None'
            intro = 'Played'
        else:
            youtube = search[15].strip()
            intro = 'None'

        if msg:
            messages.success(request, msg)

        reviews = Review.objects.filter(movie=title)
        reviews_rate = False
        if reviews:
            reviews_rate = [(range(int(review.rating)), range(int(10 - review.rating))) for review in reviews]

        full_result = {'movie': movie, 'imdb_id': imdb_id, 'title': title, 'rating': rating, 'link': link,
                       'votes': votes, 'genres': genres, 'runtime': runtime, 'mtype': mType, 'netflix': netflix,
                       'plot': plot, 'poster': poster, 'genres_split': genres_split, 'year': year, 'youtube': youtube,
                       'cast_list': cast_list, 'reviews': reviews, 'reviews_rate': reviews_rate, 'intro': intro,
                       'msg': msg}

        return render(request, "result.html", full_result)
    else:
        messages.error(request, f'Error occurred while we\'re trying to show you info about the movie!')
        return redirect('/')


def movie_search(request):
    my_watchlist = get_watchlist(request)
    if request.GET:
        movie_items = False
        if ("q" in request.GET) and request.GET["q"].strip():
            query_title = request.GET["q"]
            found_movies = list(all_movies.filter(title__icontains=query_title).order_by('-rating_id__rating'))

            page = request.GET.get('page', 1)
            paginator_search = Paginator(found_movies, 10)

            try:
                movie_items = paginator_search.page(page)
            except PageNotAnInteger:
                movie_items = paginator_search.page(1)
            except EmptyPage:
                movie_items = paginator_search.page(paginator_search.num_pages)
    else:
        movie_items = False

    return render(request, "special-item.html", {'movieItems': movie_items, 'myWatchlist': my_watchlist})


def popular(request):
    my_watchlist = get_watchlist(request)
    # popular_url = 'https://s3.amazonaws.com/popular-movies/movies.json'
    # movies = json.loads(urlopen(popular_url).read().decode())
    # popular_movies = []
    #
    # for movie in movies:
    #     try:
    #         popular_movies.append(all_movies.get(title=movie['title']))
    #     except ObjectDoesNotExist:
    #         pass
    popular_movies = list(all_movies.order_by('-release'))[:30]

    return render(request, "special-item.html", {'movieItems': popular_movies, 'myWatchlist': my_watchlist})


def error_403(request, exception=None):
    return render(request, 'errors/403.html')


def error_404(request, exception):
    return render(request, "errors/404.html", {})


def error_500(request, exception=None):
    return render(request, "errors/500.html", {})

