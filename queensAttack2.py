## solution to hackerrank problem: https://www.hackerrank.com/challenges/queens-attack-2/problem

def queensAttack(n, k, r_q, c_q, obstacles):
    # first we need to work out how many squares the queen could attack without obstacles

    #dictionary with the lengths of attack by each direction
    squareLengths = {
    'diffUp':n - r_q,
    'diffDown':r_q - 1,
    'diffLeft':c_q - 1,
    'diffRight':n - c_q,
    'squaresUpRight':min([n - r_q, n - c_q]),
    'squaresUpLeft':min([n - r_q,c_q - 1]),
    'squaresDownRight':min([r_q - 1,n - c_q]),
    'squaresDownLeft':min([r_q - 1,c_q - 1])
    }
    
    #this dictionary will find each of the closest obstacle in each direction, leaving blank if no obstacle in one direction
    lstObstacles = {
        'diffLeft':None,
        'diffRight':None,
        'diffUp':None,
        'diffDown':None,
        'squaresUpRight':None,
        'squaresUpLeft':None,
        'squaresDownRight':None,
        'squaresDownLeft':None
    }


    #we need to sort the obstacles, finding the closest in each direction and adding to this to lstObstacles
    #we only need to find closest obstacle bcos thats the only one that will impact the queens movement
    for o in obstacles:
        
        r_o = o[0]
        c_o = o[1]

        # find obstacles in each directions and add if closer than previously found
      
        # left/right
        if r_q == r_o and c_o < c_q:
            lstObstacles = addIfCloser('diffLeft', o, lstObstacles, r_q, c_q)
        elif r_q == r_o and c_o > c_q:
            lstObstacles = addIfCloser('diffRight', o, lstObstacles, r_q, c_q)

        # up/down
        elif c_q == c_o and r_o < r_q:
            lstObstacles = addIfCloser('diffDown', o, lstObstacles, r_q, c_q)
        elif c_q == c_o and r_o > r_q:
            lstObstacles = addIfCloser('diffUp', o, lstObstacles, r_q, c_q)

        # y = x axis diagonal
        elif r_o - c_o == r_q - c_q:
            if c_o > c_q:
                lstObstacles = addIfCloser('squaresUpRight', o, lstObstacles, r_q, c_q)
            elif c_o < c_q:
                lstObstacles = addIfCloser('squaresDownLeft', o, lstObstacles, r_q, c_q)

        # y = -x axis diagonal
        elif r_o + c_o == r_q + c_q:
            if c_o > c_q:
                lstObstacles = addIfCloser('squaresDownRight', o, lstObstacles, r_q, c_q)
            elif c_o < c_q:
                lstObstacles = addIfCloser('squaresUpLeft', o, lstObstacles, r_q, c_q)

    #now that we have the closest obstacle in each direction (if any) we need to calculate the squares the queen can move in each direction
    for directon in lstObstacles:

        if lstObstacles[directon]:

            r_o = lstObstacles[directon][0]
            c_o = lstObstacles[directon][1]

            if directon in ['diffRight', 'squaresUpRight', 'squaresDownRight', 'diffLeft', 'squaresDownLeft','squaresUpLeft']:
                squareLengths[directon] = abs(c_o - c_q) - 1
            elif directon in ['diffUp', 'diffDown']:
                squareLengths[directon] = abs(r_o - r_q) - 1


    # now find total squares queen can move by summing each direction 
    totalSquares = sum(squareLengths.values())
    return totalSquares

# fn to find out if the current obstacle, o, is closer than the one already stored in lstObstacles
def addIfCloser(type, o, lstObstacles, r_q, c_q):
    r_o = o[0] 
    c_o = o[1]
    if lstObstacles[type]:
        c_o2 = lstObstacles[type][1]
        if abs(c_o - c_q) < abs(c_o2 - c_q):
            lstObstacles[type] = o
    else:
        lstObstacles[type] = o    
    return lstObstacles 


assert queensAttack(5, 3, 4, 3, [(5,5), (4,2), (2,3)]) == 10
assert queensAttack(1, 0, 1, 1, []) == 0
assert queensAttack(8, 2, 4, 4, [(7,7), (8,8), (4,2), (2,6)]) == 21

with open('queensAttackTestcase.txt') as f:
    lines = f.readlines()

    n = int(lines[0].strip('\n').split(' ')[0])
    k = int(lines[0].strip('\n').split(' ')[1])
    r_q = int(lines[1].strip('\n').split(' ')[0])
    c_q = int(lines[1].strip('\n').split(' ')[1])

    lstObstacles = []
    for i in range(2,len(lines)):
        lstObstacles.append((int(lines[i].strip('\n').split(' ')[0]), int(lines[i].strip('\n').split(' ')[1])))

assert queensAttack(n, k, r_q, c_q, lstObstacles) == 40
    

